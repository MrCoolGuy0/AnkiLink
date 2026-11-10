"""Native .apkg transfers plus explicit hierarchy/settings/filter metadata.

Collection writes use Anki's APIs. SQLite edits below touch disposable exported
copies ONLY, to namespace their decks and retain receiver edits before import.
"""
from __future__ import annotations
from contextlib import closing
import copy
import base64
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
from zipfile import ZipFile,ZIP_DEFLATED

FORMAT=1
MAX_CARDS=100000
MAX_UNPACKED=1024*1024*1024
DECK_OPTIONS=('desc','extendNew','extendRev','reviewLimit','newLimit','desiredRetention')

def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,separators=(',',':'),sort_keys=True).encode()).hexdigest()
def note_hash(note):return digest([list(note.fields),[f['name'] for f in note.note_type()['flds']]])
def card_key(guid,ordinal):return guid+'#'+str(ordinal)
def quote(value):return '"'+str(value).replace('\\','\\\\').replace('"','\\"')+'"'
def clean_name(value):
    if not isinstance(value,str) or not value.strip() or len(value)>700 or any(not part.strip() for part in value.split('::')) or any(ord(c)<32 for c in value):raise ValueError('Invalid destination/deck name.')
    return value.strip()

def catalog(col):
    rows=[]
    for deck in sorted(col.decks.all(),key=lambda d:d['name'].casefold()):
        rows.append({'id':str(deck['id']),'name':deck['name'],'filtered':bool(deck.get('dyn'))})
    return rows

def checked_zip(z):
    if len(z.infolist())>100000 or sum(x.file_size for x in z.infolist())>MAX_UNPACKED:raise ValueError('The package is too large to unpack.')
    if any(x.flag_bits&1 or x.file_size>MAX_UNPACKED or x.filename.startswith('/') or '..' in Path(x.filename).parts for x in z.infolist()):raise ValueError('Invalid package entries.')
    if len(set(z.namelist()))!=len(z.namelist()):raise ValueError('Duplicate package entries.')

def source_snapshot(col,store,deck_ids,settings=True,progress=False,search=''):
    selected={int(i) for i in deck_ids};decks={int(d['id']):d for d in col.decks.all()}
    if not selected or not selected<=decks.keys():raise ValueError('Select at least one existing deck.')
    roots=[decks[i]['name'] for i in selected]
    selected_decks={did for did,d in decks.items() if any(d['name']==r or d['name'].startswith(r+'::') for r in roots)}
    ids=set()
    for did in selected:ids.update(col.find_cards('deck:'+quote(decks[did]['name'])))
    if search.strip():ids.intersection_update(col.find_cards(search))
    if not ids:raise ValueError('There are no cards in this selection. Rebuild empty filtered decks before sending.')
    if len(ids)>MAX_CARDS:raise ValueError('Send at most 100,000 cards in one transfer.')
    cards=[];notes={};homes=set()
    for cid in sorted(ids):
        card=col.get_card(cid);note=card.note();guid=note.guid;home=int(card.odid or card.did);homes.add(home)
        cards.append({'guid':guid,'ord':int(card.ord),'home':decks[home]['name'],'key':card_key(guid,card.ord),'source_id':str(cid)})
        notes[guid]={'hash':note_hash(note),'fields':list(note.fields),'field_names':[f['name'] for f in note.note_type()['flds']]}
    needed=set(selected_decks)|homes
    for d in list(needed):
        parts=decks[d]['name'].split('::')
        needed.update(did for did,deck in decks.items() if deck['name'] in ['::'.join(parts[:i]) for i in range(1,len(parts))])
    filters=[];normal=[];presets={}
    for did in sorted(needed,key=lambda i:decks[i]['name']):
        deck=decks[did]
        if deck.get('dyn'):
            if did not in selected_decks:continue
            members=[c['key'] for c in cards if int(col.get_card(int(c['source_id'])).did)==did]
            filters.append({'name':deck['name'],'members':members,'reschedule':bool(deck.get('resched',True)),
                            'terms':copy.deepcopy(deck.get('terms',[])),'again':int(deck.get('previewAgainSecs',60)),
                            'hard':int(deck.get('previewHardSecs',600)),'good':int(deck.get('previewGoodSecs',0))})
        else:
            item={'name':deck['name']}
            if settings:
                config=col.decks.config_dict_for_deck_id(did);pid=str(config['id']);presets[pid]=copy.deepcopy(config);item['preset']=pid
                item['options']={key:copy.deepcopy(deck[key]) for key in DECK_OPTIONS if key in deck}
                native=col._backend.get_deck(did).normal
                item['native_normal']=base64.b64encode(native.SerializeToString()).decode()
                item['native_fields']=[field.name for field,value in native.ListFields()]
            normal.append(item)
    manifest={'format':FORMAT,'source':store.data['identity'],'roots':roots,'cards':cards,'notes':notes,'decks':normal,'filters':filters,
              'presets':presets,'source_today':int(col.sched.today),'with_settings':bool(settings),'with_progress':bool(progress),'fsrs':bool(col.get_config('fsrs',False))}
    previous=store.data.get('last_shared',{}).get(digest(sorted(roots)),{})
    keys={c['key'] for c in cards};old=set(previous.get('keys',[]));old_hashes=previous.get('notes',{})
    manifest['summary']={'title':', '.join(roots)[:150],'cards':len(cards),'new_cards':len(keys-old),
                         'edited_notes':sum(g in old_hashes and old_hashes[g]!=n['hash'] for g,n in notes.items()),
                         'settings':bool(settings),'progress':bool(progress),'filtered_decks':len(filters),'roots':roots}
    return manifest,sorted(ids)

def repack_apkg(source,target,mutate):
    """Rewrite only the SQLite payload in a temporary native legacy package."""
    with tempfile.TemporaryDirectory() as directory,ZipFile(source) as original:
        checked_zip(original)
        if 'collection.anki21' not in original.namelist():raise ValueError('This transfer needs Anki’s modern native .apkg exporter.')
        database=Path(directory)/'copy.anki2';database.write_bytes(original.read('collection.anki21'))
        mutate(database)
        with ZipFile(target,'w',ZIP_DEFLATED) as out:
            for item in original.infolist():out.writestr(item.filename,database.read_bytes() if item.filename=='collection.anki21' else original.read(item))

def make_bundle(col,store,deck_ids,out_path,settings=True,progress=False,search=''):
    from anki.collection import Collection,ExportAnkiPackageOptions,CardIdsLimit
    manifest,ids=source_snapshot(col,store,deck_ids,settings,progress,search)
    with tempfile.TemporaryDirectory() as directory:
        original=Path(directory)/'source.apkg';cleaned=Path(directory)/'decks.apkg'
        # Source export is read-only. Original schedules are used only in this
        # temporary copy; OFF strips them before anything can be uploaded.
        col.export_anki_package(out_path=str(original),options=ExportAnkiPackageOptions(with_scheduling=True,with_deck_configs=False,with_media=True,legacy=True),limit=CardIdsLimit(card_ids=ids))
        def clean(database):
            stage=Collection(str(database))
            try:
                for d in list(stage.decks.all()):
                    if d.get('dyn'):
                        stage.sched.empty_filtered_deck(d['id']);stage.decks.remove([d['id']])
                # Evaluate the original filter rules against restored sender
                # schedules, before stripping progress. This preserves two-rule
                # membership/order even when all receiver cards will start New.
                by_source={int(c['source_id']):c['key'] for c in manifest['cards']}
                for filt in manifest['filters']:
                    remaining={cid for cid,key in by_source.items() if key in filt['members']};groups=[]
                    for query,limit,order in filt['terms'][:2]:
                        matched=remaining.intersection(stage.find_cards(query));remaining-=matched
                        groups.append({'members':[by_source[cid] for cid in sorted(matched)],'limit':int(limit),'order':int(order)})
                    if not groups:groups=[{'members':[],'limit':len(remaining),'order':1}]
                    groups[-1]['members'].extend(by_source[cid] for cid in sorted(remaining));filt['groups']=groups
                if not progress:stage.sched.schedule_cards_as_new(stage.find_cards(''),reset_counts=True,restore_position=True)
            finally:stage.close(downgrade=True)
            # SQLite's transaction context commits/rolls back but does not
            # close its file handle. Close before TemporaryDirectory cleanup
            # (Windows cannot remove an open database), including on errors.
            with closing(sqlite3.connect(database)) as db,db:
                # Native exports may include sibling cards for selected notes.
                # Restrict the disposable copy to the exact selected card IDs.
                db.execute('CREATE TEMP TABLE selected_card_ids(id INTEGER PRIMARY KEY)')
                db.executemany('INSERT INTO selected_card_ids VALUES(?)',[(cid,) for cid in ids])
                db.execute('DELETE FROM cards WHERE id NOT IN (SELECT id FROM selected_card_ids)')
                db.execute('DELETE FROM notes WHERE id NOT IN (SELECT nid FROM cards)')
                db.execute('DELETE FROM revlog WHERE cid NOT IN (SELECT id FROM selected_card_ids)')
                if not progress:
                    db.execute('DELETE FROM revlog')
                    decks=json.loads(db.execute('SELECT decks FROM col').fetchone()[0])
                    for deck in decks.values():
                        for name in ('newToday','revToday','lrnToday','timeToday'):deck[name]=[0,0]
                    db.execute('UPDATE col SET decks=?',(json.dumps(decks),))
                    for nid,tags in db.execute('SELECT id,tags FROM notes').fetchall():
                        clean_tags=' '+' '.join(tag for tag in tags.split() if tag.lower() not in ('marked','leech'))+' '
                        db.execute('UPDATE notes SET tags=? WHERE id=?',(clean_tags,nid))
        repack_apkg(original,cleaned,clean)
        manifest['package_sha256']=hashlib.sha256(cleaned.read_bytes()).hexdigest()
        with ZipFile(out_path,'w',ZIP_DEFLATED) as bundle:
            bundle.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False));bundle.write(cleaned,'decks.apkg')
    return manifest

def read_bundle(path):
    with ZipFile(path) as z:
        checked_zip(z)
        if set(z.namelist())!={'manifest.json','decks.apkg'}:raise ValueError('This is not an AnkiLink deck package.')
        if z.getinfo('manifest.json').file_size>60*1024*1024:raise ValueError('The transfer index is too large.')
        m=json.loads(z.read('manifest.json'));raw=z.read('decks.apkg')
    if m.get('format')!=FORMAT or not isinstance(m.get('source'),str) or not re_source(m['source']):raise ValueError('Unsupported AnkiLink package format.')
    cards=m.get('cards',[])
    if not isinstance(cards,list) or not 1<=len(cards)<=MAX_CARDS or len({c.get('key') for c in cards})!=len(cards):raise ValueError('Invalid card index.')
    if hashlib.sha256(raw).hexdigest()!=m.get('package_sha256'):raise ValueError('The deck download is incomplete.')
    for deck in m.get('decks',[])+m.get('filters',[]):clean_name(deck['name'])
    normal_names={d['name'] for d in m.get('decks',[])};filter_names={d['name'] for d in m.get('filters',[])}
    if any(c.get('home') not in normal_names for c in cards):raise ValueError('A card home deck is missing from the transfer hierarchy.')
    if normal_names&filter_names or any(name.startswith(f+'::') for name in normal_names|filter_names for f in filter_names):raise ValueError('Invalid filtered-deck hierarchy.')
    # The signed-in sender controls the package, but the card-count preview must
    # still describe its actual content, rather than trusting a JSON claim.
    with tempfile.TemporaryDirectory() as directory,ZipFile(path) as bundle:
        apkg=Path(directory)/'check.apkg';apkg.write_bytes(raw)
        with ZipFile(apkg) as z:
            checked_zip(z)
            if 'collection.anki21' not in z.namelist():raise ValueError('Unsupported deck payload.')
            database=Path(directory)/'check.sqlite';database.write_bytes(z.read('collection.anki21'))
            with closing(sqlite3.connect(database)) as db,db:
                actual={card_key(guid,ordinal) for guid,ordinal in db.execute('SELECT n.guid,c.ord FROM cards c JOIN notes n ON n.id=c.nid')}
                if actual!={c['key'] for c in cards}:raise ValueError('The package cards do not match its preview.')
                for guid,fields in db.execute('SELECT guid,flds FROM notes'):
                    if guid not in m['notes'] or fields.split('\x1f')!=m['notes'][guid]['fields']:raise ValueError('The package notes do not match its preview.')
    return m,raw

def re_source(value):return len(value)==32 and all(c in '0123456789abcdef' for c in value)

def existing_index(col,manifest):
    # No replacement queue; these are identity lookups for native import only.
    wanted=set(manifest['notes']);notes={};cards={}
    for nid,guid in col.db.all('SELECT id,guid FROM notes'):
        if guid not in wanted:continue
        note=col.get_note(nid);notes[guid]=note
        for card in note.cards():cards[card_key(guid,card.ord)]=card.id
    return notes,cards

def deck_destination(name,root=''):
    return clean_name(root+'::'+name if root else name)

def merge_card_locations(col,manifest,cards,legacy_roots,build_filters,known_notes):
    """Move only selected shared card identities; retain their review state."""
    moves={};borrowed=[];moved=0;previous_folders=set()
    deck_names={d['id']:d['name'] for d in col.decks.all()}
    old_names={deck_destination(f['name'],root).casefold() for root in legacy_roots for f in manifest['filters']}
    old_filters={d['id'] for d in col.decks.all() if d['name'].casefold() in old_names}
    homes={name:col.decks.id(deck_destination(name)) for name in {c['home'] for c in manifest['cards']}}
    for item in manifest['cards']:
        cid=cards.get(item['key'])
        if cid is None:continue
        card=col.get_card(cid);home=homes[item['home']]
        # A receiver may already have dragged the received branch elsewhere.
        # Only track folders of notes actually received from this sender before.
        if (card.odid or card.did)!=home and item['guid'] in known_notes:
            old_name=deck_names[card.odid or card.did];parts=old_name.split('::')
            previous_folders.update('::'.join(parts[:i]) for i in range(1,len(parts)+1))
        if card.odid:
            if build_filters and card.did in old_filters:
                # Native Set Deck restores only these selected cards out of
                # their old received filter, before the requested rebuild.
                moves.setdefault(home,[]).append(cid);moved+=1
            elif card.odid!=home:
                card.odid=home;borrowed.append(card);moved+=1
        elif card.did!=home:
            moves.setdefault(home,[]).append(cid);moved+=1
    for did,ids in moves.items():col.set_deck(ids,did)
    for start in range(0,len(borrowed),500):col.update_cards(borrowed[start:start+500])
    return moved,previous_folders

def remove_empty_received_folders(col,manifest,roots,previous_folders):
    """Only old sender folders and included paths, never cards or other branches."""
    candidates=set(previous_folders)
    for root in roots:
        candidates.add(root)
        for item in manifest['decks']+manifest['filters']:
            parts=item['name'].split('::')
            candidates.update(deck_destination('::'.join(parts[:i]),root) for i in range(1,len(parts)+1))
    removed=0
    for name in sorted(candidates,key=lambda n:n.count('::'),reverse=True):
        did=col.decks.id_for_name(name)
        if not did or did==1:continue
        prefix=col.decks.get(did)['name'].casefold()+'::'
        if any(d['name'].casefold().startswith(prefix) for d in col.decks.all()):continue
        if col.db.all('SELECT id FROM cards WHERE did=? OR odid=? LIMIT 1',did,did):continue
        col.decks.remove([did]);removed+=1
    return removed

def preview(col,store,path):
    m,_=read_bundle(path);notes,cards=existing_index(col,m);lineage=store.data.get('lineage',{}).get(m['source'],{})
    conflicts=[];updates=0
    for guid,note in notes.items():
        incoming=m['notes'][guid];local=note_hash(note)
        if local==incoming['hash']:continue
        if local!=lineage.get(guid):conflicts.append({'guid':guid,'local':list(note.fields),'received':incoming['fields']})
        else:updates+=1
    return {'manifest':m,'merge':store.data.get('import_modes',{}).get(m['source'],True),'destination':store.data.get('destinations',{}).get(m['source'],''),'new_cards':sum(c['key'] not in cards for c in m['cards']),'existing_cards':sum(c['key'] in cards for c in m['cards']),
            'updated_notes':updates,'conflicts':conflicts,'needs_fsrs':m.get('fsrs',False) and not col.get_config('fsrs',False)}

def apply_bundle(col,store,path,options,receipt):
    from anki.collection import ImportAnkiPackageRequest,ImportAnkiPackageOptions
    from anki.import_export_pb2 import IMPORT_ANKI_PACKAGE_UPDATE_CONDITION_ALWAYS as ALWAYS
    m,raw=read_bundle(path);report=preview(col,store,path);source=m['source'];merge=options.get('merge') is True
    root='' if merge else clean_name(options.get('destination','Shared'))
    legacy_roots=set(store.data.get('legacy_destinations',{}).get(source,[]))
    previous=store.data.get('destinations',{}).get(source)
    if previous:legacy_roots.add(clean_name(previous))
    prior=store.data.get('imports',{}).get(receipt)
    if prior and prior.get('done'):return prior['result']
    settings=options.get('settings') is True and m.get('with_settings') is True
    progress=options.get('progress') is True and m.get('with_progress') is True
    reset=options.get('reset') is True
    if progress and reset:raise ValueError('Choose either copied progress or a reset, not both.')
    if settings and report['needs_fsrs'] and not options.get('enable_fsrs'):raise ValueError('This setup needs FSRS. Accept the FSRS option or keep your own settings.')
    if settings:
        fields=set(col.decks.new_deck().normal.DESCRIPTOR.fields_by_name)
        if any(set(d.get('native_fields',[]))-fields for d in m['decks']):raise ValueError('The sender’s deck setup needs a newer Anki version. Update Anki or keep your own settings.')
    local_notes,old_cards=existing_index(col,m)
    for guid,note in local_notes.items():
        if [f['name'] for f in note.note_type()['flds']]!=m['notes'][guid]['field_names']:raise ValueError('A received note type has different fields. Resolve that note type in Anki before accepting this transfer.')
    keep={c['guid'] for c in report['conflicts']} if not options.get('replace_conflicts') else set()
    # Check namespace/type collisions before the first receiver collection write.
    for item in m['decks']+m['filters']:
        name=deck_destination(item['name'],root);parts=name.split('::')
        for index in range(1,len(parts)+1):
            current='::'.join(parts[:index]);did=col.decks.id_for_name(current)
            if not did:continue
            expected_filtered=index==len(parts) and item in m['filters']
            if bool(col.decks.get(did).get('dyn'))!=expected_filtered:raise ValueError('A different deck type already uses '+current+'. Choose another destination folder.')
    # A retry may complete a previously interrupted native import, but never
    # performs a second completed reset/import after a stored receipt.
    with tempfile.TemporaryDirectory() as directory:
        original=Path(directory)/'incoming.apkg';staged=Path(directory)/'prepared.apkg';original.write_bytes(raw)
        def prepare(database):
            with closing(sqlite3.connect(database)) as db,db:
                row=db.execute('SELECT decks FROM col').fetchone();decks=json.loads(row[0])
                allowed={d['name'] for d in m['decks']}
                decks={key:deck for key,deck in decks.items() if deck['name'] in allowed}
                for deck in decks.values():
                    deck['name']=deck_destination(deck['name'],root);deck['conf']=1
                db.execute('UPDATE col SET decks=?',(json.dumps(decks),))
                for guid in keep:
                    note=local_notes[guid];db.execute('UPDATE notes SET flds=?,tags=? WHERE guid=?',('\x1f'.join(note.fields),' '+' '.join(note.tags)+' ',guid))
        repack_apkg(original,staged,prepare)
        # One standard Anki backup before explicit receiver-side changes.
        backups=store.folder/'backups';backups.mkdir(exist_ok=True)
        col.create_backup(backup_folder=str(backups),force=True,wait_for_completion=True)
        col.import_anki_package(ImportAnkiPackageRequest(package_path=str(staged),options=ImportAnkiPackageOptions(
            merge_notetypes=True,update_notes=ALWAYS,update_notetypes=ALWAYS,with_scheduling=progress,with_deck_configs=False)))
    # Some Anki releases classify equal-second note mtimes as duplicates even
    # with ALWAYS. Apply explicitly accepted field changes through the public
    # note API, without inventing future timestamps or touching review data.
    refreshed,_=existing_index(col,m)
    for guid,note in refreshed.items():
        if guid in keep or guid not in local_notes:continue
        fields=m['notes'][guid]['fields']
        if list(note.fields)!=fields:note.fields[:]=fields;col.update_note(note)
    _,cards=existing_index(col,m)
    # Import can generate unselected sibling clozes/templates. Remove ONLY
    # siblings created by this import, retaining every pre-existing receiver card.
    wanted={c['key'] for c in m['cards']}
    extras=[cid for key,cid in cards.items() if key not in wanted and key not in old_cards]
    if extras:col.remove_cards_and_orphaned_notes(extras);_,cards=existing_index(col,m)
    moved,previous_folders=merge_card_locations(col,m,cards,legacy_roots,options.get('build_filters',True) is True,store.data.get('lineage',{}).get(source,{})) if merge else (0,set())
    if settings:
        if report['needs_fsrs']:col.set_config('fsrs',True)
        configs={}
        # New private presets every explicitly accepted settings transfer prevent
        # edits to a preset from changing unrelated receiver decks.
        for pid,config in m['presets'].items():configs[pid]=col.decks.add_config('AnkiLink · '+str(config.get('name','Setup')),clone_from=config)['id']
        for item in m['decks']:
            did=col.decks.id(deck_destination(item['name'],root));deck=col.decks.get(did)
            deck.update(copy.deepcopy(item.get('options',{})));deck['conf']=configs[item['preset']];col.decks.update_dict(deck)
            if item.get('native_normal'):
                native=col._backend.get_deck(did);native.normal.ParseFromString(base64.b64decode(item['native_normal']));native.normal.config_id=configs[item['preset']]
                for key in ('new_limit_today','review_limit_today'):
                    if key in native.normal.DESCRIPTOR.fields_by_name and native.normal.HasField(key):
                        limit=getattr(native.normal,key)
                        if limit.today==m.get('source_today'):limit.today=int(col.sched.today)
                        else:native.normal.ClearField(key)
                col._backend.update_deck(native)
    else:
        for item in m['decks']:col.decks.id(deck_destination(item['name'],root))
    selected_ids=[cards[c['key']] for c in m['cards'] if c['key'] in cards]
    if reset:
        col.sched.schedule_cards_as_new(selected_ids,reset_counts=True,restore_position=True)
    filtered=[];build=options.get('build_filters',True) is True
    mapping=store.data.setdefault('lineage',{}).setdefault(source,{})
    for guid,incoming in m['notes'].items():
        if guid not in keep:mapping[guid]=incoming['hash']
    # Filter definitions use receiver card IDs, never the sender's is:due query.
    for item in m['filters']:
        name=deck_destination(item['name'],root);did=col.decks.id_for_name(name)
        if did and not col.decks.get(did).get('dyn'):raise ValueError('A regular deck already uses the filtered deck name: '+name)
        update=col.sched.get_or_create_filtered_deck(did or 0);update.name=name
        config=update.config
        if settings or not did:config.reschedule=bool(item['reschedule']) if settings else False
        if settings:
            config.preview_again_secs=item['again'];config.preview_hard_secs=item['hard'];config.preview_good_secs=item['good']
        ids=[cards[key] for key in item['members'] if key in cards]
        old_orders=[t.order for t in config.search_terms]
        groups=item.get('groups') or [{'members':item['members'],'limit':len(ids),'order':int(item['terms'][0][2]) if item.get('terms') else 1}]
        del config.search_terms[:]
        for index,group in enumerate(groups[:2]):
            group_ids=[cards[key] for key in group['members'] if key in cards];term=config.search_terms.add()
            term.search='cid:'+','.join(map(str,group_ids)) if group_ids else 'cid:0'
            term.limit=max(1,len(group_ids),int(group.get('limit',0)))
            term.order=int(group['order']) if settings else (old_orders[min(index,len(old_orders)-1)] if did and old_orders else 1)
        # The scheduler's add_or_update_filtered_deck() also rebuilds immediately.
        # Save through the native deck API instead, so "build later" is real and
        # empty/overlapping definitions can be delivered without forced moves.
        legacy=col.decks.get(did) if did else col.decks.new_deck_legacy(True)
        legacy.update(name=name,resched=config.reschedule,terms=[[t.search,t.limit,t.order] for t in config.search_terms],
                      previewAgainSecs=config.preview_again_secs,previewHardSecs=config.preview_hard_secs,previewGoodSecs=config.preview_good_secs)
        if did:col.decks.update_dict(legacy)
        else:did=col.decks.add_deck_legacy(legacy).id
        count=col.sched.rebuild_filtered_deck(did).count if build else len(col.find_cards('deck:'+quote(name)))
        filtered.append({'name':name,'selected':len(ids),'built':count})
    removed=remove_empty_received_folders(col,m,legacy_roots,previous_folders) if merge else 0
    result={'cards':len(selected_ids),'new_cards':report['new_cards'],'kept_local_edits':len(keep),'filtered':filtered,'destination':root,'merge':merge,'moved_cards':moved,'removed_empty_decks':removed}
    store.data.setdefault('import_modes',{})[source]=merge
    if merge:store.data.setdefault('legacy_destinations',{})[source]=sorted(legacy_roots)
    store.data.setdefault('destinations',{})[source]=root
    store.data.setdefault('imports',{})[receipt]={'done':True,'result':result};store.save()
    return result

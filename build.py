"""Allowlisted deterministic packages; no local accounts, credentials or QA data."""
from pathlib import Path
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
import hashlib
import json
import argparse
import subprocess

ROOT=Path(__file__).resolve().parent
PACKAGE=['sidebar.py','notifications.py','avatar_crop.py','live.py','media.py','__init__.py','manifest.json','config.py','net.py','transfer.py','dialog.py','web/index.html','web/app.css','web/controls.css','web/retro.css','web/rise.css','web/message.css','web/retro-flower.svg','web/app.js','README.md']
SERVER=['server.py','Dockerfile','compose.yaml','Caddyfile','.env.example']
DOCS=['UI-NOTICES-VALIDATION.md','REACTIONS-GROUPS-VALIDATION.md','tests/test_reactions_groups.cjs','tests/test_reactions_server.py','CONTINUE-HERE.md','HOST-MIGRATION-VALIDATION.md','tests/test_config.py','DELIVERY-REQUIREMENTS.md','GROUP-SHARING-VALIDATION.md','tests/test_group_sharing.py','tests/test_group_sharing.cjs','tests/test_group_share_controller.py','tests/test_sidebar.cjs','tests/test_notifications.py','tests/test_window_state.py','tests/test_groups.py','tests/test_groups.cjs','tests/test_actions.py','tests/test_actions.cjs','tests/test_background_jobs.py','ADDON-PERFORMANCE-AUDIT.md','tests/test_avatar_crop.py','tests/render_profile_qt.py','tests/test_avatar.py','tests/test_live.py','tests/benchmark_live.py','tests/test_merge.py','tests/benchmark_hosted.py','tests/test_transport.py','tests/test_sticker_media.py','tests/test_messages.cjs','tests/test_message_controller.py','tests/test_windows_locks.py','README.md','SERVER-SETUP.md','HOSTED-SERVICE.md','START-HERE.md','VALIDATION.md','build.py','tests/test_relay.py','tests/test_transfer.py','tests/test_ui_qt.py','tests/test_native_webview.py','tests/test_button_styles_qt.py','tests/test_startup.cjs']
DOCS=list(dict.fromkeys(DOCS+sorted(str(p.relative_to(ROOT)) for p in (ROOT/'tests').glob('test_*') if p.is_file() and p.suffix in ('.py','.cjs'))))
HOSTED_SUPPORT=['START-HERE.md','DATA-BACKUP.md','RESTORE-HOSTING.md','VALIDATION.md',
 'portable/package.json','portable/package-lock.json','portable/worker.ts','portable/relay-qa.mjs','portable/wrangler.example.jsonc',
 'history/SOURCE-PROVENANCE-v1.4.0.json','history/START-HERE-v1.2.0.md','history/VALIDATION-v1.2.0.md','history/SOURCE-PROVENANCE-v1.2.0.json']

def archive(path,entries):
    temporary=path.with_name(path.name+'.tmp')
    try:
        with ZipFile(temporary,'w',ZIP_DEFLATED,compresslevel=9) as z:
            for name,data in sorted(entries.items()):
                entry=ZipInfo(name,date_time=(2026,10,30,0,0,0));entry.compress_type=ZIP_DEFLATED;entry.external_attr=0o100644<<16;z.writestr(entry,data)
        with ZipFile(temporary) as z:assert z.testzip() is None
        temporary.replace(path)
    finally:temporary.unlink(missing_ok=True)

def hosted_entries(args):
    root=ROOT/'hosted-server';entries={name:(root/name).read_bytes() for name in HOSTED_SUPPORT}
    if args.hosted_repo:
        repo=Path(args.hosted_repo).resolve()
        def git(*values):return subprocess.check_output(['git','-C',str(repo),*values])
        commit=git('rev-parse','HEAD').decode().strip()
        record=json.loads(Path(args.deployment_record).read_text())
        assert record['source_commit']==commit,'Deployment must match the exact source commit.'
        names=git('ls-tree','-rz','--name-only',commit).decode().split('\0')
        exact={name:git('show',commit+':'+name) for name in names if name}
        provenance={**record,'hosted_service_version':record.get('hosted_service_version','1.5.2'),'desktop_version':json.loads((ROOT/'anki_link/manifest.json').read_text())['version'],
                    'tracked_files_sha256':{n:hashlib.sha256(b).hexdigest() for n,b in exact.items()},
                    'live_data_included':False,'secrets_included':False}
    else:
        provenance=json.loads((root/'SOURCE-PROVENANCE.json').read_text())
        hashes=provenance['tracked_files_sha256']
        exact={name:(root/'exact-hosted-source'/name).read_bytes() for name in hashes}
        assert all(hashlib.sha256(exact[n]).hexdigest()==d for n,d in hashes.items())
    entries.update({'exact-hosted-source/'+name:data for name,data in exact.items()})
    entries['SOURCE-PROVENANCE.json']=(json.dumps(provenance,indent=2)+'\n').encode()
    entries['CHECKSUMS.json']=(json.dumps({n:hashlib.sha256(b).hexdigest() for n,b in entries.items()},indent=2)+'\n').encode()
    return {'hosted-server/'+name:data for name,data in entries.items()}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--installer-only',action='store_true');parser.add_argument('--hosted-repo');parser.add_argument('--deployment-record');args=parser.parse_args()
    if args.hosted_repo and not args.deployment_record:parser.error('--hosted-repo requires --deployment-record')
    package=ROOT/'anki_link';version=json.loads((package/'manifest.json').read_text())['version'];out=ROOT/'dist';out.mkdir(exist_ok=True)
    (package/'README.md').write_bytes((ROOT/'README.md').read_bytes())
    files={name:(package/name).read_bytes() for name in PACKAGE}
    for name,data in files.items():
        if name.endswith('.py'):compile(data,name,'exec')
    installer=out/f'AnkiLink-v{version}.ankiaddon';archive(installer,files)
    server_files={name:(ROOT/'server'/name).read_bytes() for name in SERVER};server_files['SERVER-SETUP.md']=(ROOT/'SERVER-SETUP.md').read_bytes()
    server=out/f'AnkiLink-Server-v{version}.zip';archive(server,server_files)
    outputs=[installer,server]
    if args.installer_only:
        print(json.dumps([{'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in outputs],indent=2));return
    handoff={f'anki_link/{name}':data for name,data in files.items()};handoff.update({'server/'+name:data for name,data in server_files.items()})
    handoff.update({name:(ROOT/name).read_bytes() for name in DOCS});handoff['dist/'+installer.name]=installer.read_bytes();handoff['dist/'+server.name]=server.read_bytes()
    handoff.update(hosted_entries(args))
    checks={name:hashlib.sha256(data).hexdigest() for name,data in handoff.items()};handoff['CHECKSUMS.json']=(json.dumps(checks,indent=2)+'\n').encode()
    bundle=out/f'AnkiLink-Full-Source-v{version}.zip';archive(bundle,handoff)
    print(json.dumps([{'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in (installer,server,bundle)],indent=2))

if __name__=='__main__':main()

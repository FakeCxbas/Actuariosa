"""Verify a Nexo backup and restore it into a NEW portable SQLite file.
Usage: python3 scripts/restore-backup.py backup.json new-database.sqlite
Never connects to production or overwrites an existing destination.
"""
import hashlib,json,sqlite3,sys,pathlib,os

def restore(source,target):
    target=pathlib.Path(target)
    if target.exists():raise ValueError('La base de destino ya existe. No se sobrescribirá.')
    envelope=json.loads(pathlib.Path(source).read_text())
    if envelope.get('format')!='nexo-backup-v1' or envelope.get('schemaVersion')!=2:raise ValueError('Formato de copia incompatible')
    payload=envelope['payload']
    if hashlib.sha256(payload.encode()).hexdigest()!=envelope['sha256']:raise ValueError('La huella no coincide: el archivo está dañado o fue modificado')
    data=json.loads(payload)
    tables=['suppliers','branches','products','stock','movements','audit','app_state']
    if set(data)!=set(tables):raise ValueError('La copia no contiene todas las tablas esperadas')
    # Exclusive create prevents accidental overwrite, including competing processes.
    fd=os.open(target,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
    c=sqlite3.connect(target)
    try:
        root=pathlib.Path(__file__).resolve().parents[1]
        for migration in sorted((root/'drizzle').glob('*.sql')):c.executescript(migration.read_text())
        triggers=c.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'").fetchall()
        for name,_ in triggers:c.execute('DROP TRIGGER "'+name+'"')
        c.execute('PRAGMA foreign_keys=ON')
        for table in tables:
            allowed={r[1] for r in c.execute('PRAGMA table_info("'+table+'")')}
            for row in data[table]:
                if set(row)!=allowed:raise ValueError('Columnas incompatibles en '+table)
                columns=','.join('"'+k+'"' for k in row)
                c.execute('INSERT INTO "'+table+'" ('+columns+') VALUES ('+','.join('?' for _ in row)+')',list(row.values()))
        for _,sql in triggers:c.execute(sql)
        if c.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Referencias inconsistentes')
        if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Integridad fallida')
        c.commit();c.close()
        print('Copia verificada y restaurada en una base NUEVA:',target)
    except Exception:
        c.close();target.unlink(missing_ok=True);raise

if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit(__doc__)
    restore(sys.argv[1],sys.argv[2])

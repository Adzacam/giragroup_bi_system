from pathlib import Path

p = Path("backend/routers/auth.py")
text = p.read_text(encoding="utf-8")

old = "def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):\n    ident = req.email.strip()\n    user = db.query(User).filter("
new = "def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):\n    ident = req.email.strip()\n    temp_password = None\n    user = db.query(User).filter("

if "\r\n" in text:
    old = old.replace("\n", "\r\n")
    new = new.replace("\n", "\r\n")

if old in text:
    text = text.replace(old, new, 1)
    p.write_text(text, encoding="utf-8")
    print("auth.py actualizado con temp_password = None.")
else:
    print("No se encontró el target.")

"""
auth.py — Gestion authentification DuxSalary
"""
from functools import wraps
from flask import session, redirect, url_for, request
from database import get_user_by_email, verify_password

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def authenticate(email, password):
    user = get_user_by_email(email)
    if user and verify_password(password, user['password_hash']):
        return user
    return None

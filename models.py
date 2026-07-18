from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, timezone

db = SQLAlchemy()

class Trip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(25), nullable=False)
    code = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc) + timedelta(days=10))
    participants = db.relationship('Participant', backref='trip', lazy=True)
    expenses = db.relationship('Expense', backref='trip', lazy=True, order_by='Expense.created_at.desc()')


class Participant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)
    name = db.Column(db.String(30), nullable=False)
    session_token = db.Column(db.String(64), unique=True)


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)
    paid_by = db.Column(db.Integer, db.ForeignKey('participant.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    splits = db.relationship('ExpenseSplit', backref='expense', lazy=True)
    payer = db.relationship('Participant', foreign_keys=[paid_by])


class ExpenseSplit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey('expense.id'), nullable=False)
    participant_id = db.Column(db.Integer, db.ForeignKey('participant.id'), nullable=False)
    share_amount = db.Column(db.Float, nullable=False)
                           
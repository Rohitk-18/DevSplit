from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import db, Trip, Participant, Expense, ExpenseSplit
from itsdangerous import URLSafeTimedSerializer
from types import SimpleNamespace
import os, secrets
from utils import calculate_settlements
from datetime import datetime, timezone
from sqlalchemy import func

main = Blueprint('main', __name__)
s = URLSafeTimedSerializer(os.getenv('SECRET_KEY', 'dev-secret-key'))


@main.route('/')
def home():
    return render_template('index.html')

@main.route('/create', methods=['POST'])
def create_trip():
    trip_name = request.form.get('trip_name')

    if not trip_name:
        return redirect(url_for('main.home'))
    
    code = s.dumps(trip_name + str(os.urandom(8)))[:32]
    
    trip = Trip(name=trip_name, code=code)
    db.session.add(trip)
    db.session.commit()

    return redirect(url_for('main.trip_page', code=code))

@main.route('/trip/<code>')
def trip_page(code):
    trip = Trip.query.filter_by(code=code).first_or_404()
    if trip.expires_at < datetime.now():
        flash("Trip Expired!")
        return redirect(url_for('main.home'))
    current_member = None
    if 'session_token' in session:
        current_member=Participant.query.filter_by(session_token=session['session_token'], trip_id=trip.id).first()
    settlements = calculate_settlements(trip.participants)
    
    return render_template('trip.html', trip=trip, current_member=current_member, settlements = settlements)


@main.route('/trip/<code>/join', methods=['POST'])
def join_trip(code):
    trip = Trip.query.filter_by(code=code).first_or_404()
    if trip.expires_at < datetime.now():
        flash("Trip Expired!")
        return redirect(url_for('main.home'))
    user_name = request.form.get('name', '').strip()

    if not user_name:
        flash("Name cannot be empty!")
        return redirect(url_for('main.trip_page', code=code))

    normalized_name = user_name.lower()
    display_name = user_name.title()

    current_session = session.get('session_token')
    if current_session and Participant.query.filter_by(session_token=current_session, trip_id=trip.id).first():
        return redirect(url_for('main.trip_page', code=code))

    existing = Participant.query.filter(Participant.trip_id == trip.id, func.lower(Participant.name) == normalized_name).first()
    if existing:
        flash("A participant with this name already exists!")
        return redirect(url_for('main.trip_page', code=code))

    token = secrets.token_hex(32)
    member = Participant(name = display_name, trip_id = trip.id, session_token = token)

    db.session.add(member)
    db.session.commit()

    session['session_token'] = token
    return redirect(url_for('main.trip_page', code = code))


@main.route('/trip/<code>/add_expense', methods=['POST'])
def add_expense(code):
    trip=Trip.query.filter_by(code=code).first_or_404()
    if trip.expires_at < datetime.now():
        flash("Trip Expired!")
        return redirect(url_for('main.home'))
    paid_by=None
    if 'session_token' in session:
        paid_by=Participant.query.filter_by(session_token=session['session_token']).first()
    description=request.form.get('description')
    amount=float(request.form.get('amount'))
    if amount <= 0:
        flash("Amount must be greater than zero!")
        return redirect(url_for('main.trip_page', code = code))
    
    split_among=request.form.getlist('split_among')
    if not split_among:
        flash("Please select atleast one person to split with!")
        return redirect(url_for('main.trip_page', code = code))
    expense=Expense(trip_id=trip.id, paid_by=paid_by.id, amount=amount, description=description)
    db.session.add(expense)
    db.session.commit()

    share=amount / len(split_among)
    for user in split_among:
        expense_split = ExpenseSplit(expense_id=expense.id, participant_id=int(user), share_amount=share)
        db.session.add(expense_split)

    db.session.commit()
    return redirect(url_for('main.trip_page', code=code))
    


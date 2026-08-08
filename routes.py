from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort
from models import db, Trip, Participant, Expense, ExpenseSplit
from itsdangerous import URLSafeTimedSerializer
from types import SimpleNamespace
import os, secrets, re
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
        trip_tokens = session.get('trip_tokens', {})
        trip_tokens.pop(trip.code, None)
        session['trip_tokens'] = trip_tokens
        session.modified = True
        flash("Trip Expired!")
        return redirect(url_for('main.home'))
    current_member = None
    trip_tokens = session.get('trip_tokens', {})
    token = trip_tokens.get(trip.code)
    if token:
        current_member = Participant.query.filter_by(session_token=token, trip_id=trip.id).first()
    
    if current_member is None:
        return redirect(url_for('main.join_trip', code=trip.code))
    settlements = calculate_settlements(trip.participants)
    return render_template('trip.html', trip=trip, current_member=current_member, settlements = settlements)


@main.route('/trip/<code>/join', methods=['GET', 'POST'])
def join_trip(code):
    trip = Trip.query.filter_by(code=code).first_or_404()
    if trip.expires_at < datetime.now():
        flash("Trip Expired!")
        return redirect(url_for('main.home'))
    
    if request.method == 'GET':
        return render_template('join.html', trip=trip)
    
    user_name = request.form.get('name', '').strip()
    
    if not user_name:
        flash("Name cannot be empty!")
        return redirect(url_for('main.join_trip', code=code))

    if len(user_name) > 50:
        flash("Name cannot exceed 50 characters.")
        return redirect(url_for('main.join_trip', code=code))

    if not re.fullmatch(r"[A-Za-z ]+", user_name):
        flash("Name can only contain letters and spaces.")
        return redirect(url_for("main.join_trip", code=code))
        

    normalized_name = user_name.lower()
    display_name = user_name.title()

    trip_tokens = session.get('trip_tokens', {})
    current_token = trip_tokens.get(trip.code)
    if current_token and Participant.query.filter_by(session_token=current_token, trip_id=trip.id).first():
        return redirect(url_for('main.trip_page', code=code))

    existing = Participant.query.filter(Participant.trip_id == trip.id, func.lower(Participant.name) == normalized_name).first()
    if existing:
        flash("A participant with this name already exists!")
        return redirect(url_for('main.join_trip', code=code))

    token = secrets.token_hex(32)
    member = Participant(name = display_name, trip_id = trip.id, session_token = token)

    db.session.add(member)
    db.session.commit()

    trip_tokens = session.get("trip_tokens", {})
    trip_tokens[trip.code] = token

    session["trip_tokens"] = trip_tokens
    session.permanent = True
    return redirect(url_for('main.trip_page', code = code))


@main.route('/trip/<code>/add_expense', methods=['POST'])
def add_expense(code):
    trip=Trip.query.filter_by(code=code).first_or_404()
    if trip.expires_at < datetime.now():
        flash("Trip Expired!")
        return redirect(url_for('main.home'))

    session_token = session.get("trip_tokens", {}).get(trip.code)

    paid_by = Participant.query.filter_by(trip_id=trip.id, session_token=session_token).first()
    if not paid_by:
        flash("Please join the trip first.")
        return redirect(url_for('main.join_trip', code=trip.code))

    
    description=request.form.get('description', '').strip()
    if not re.fullmatch(r"[A-Za-z0-9\s.,()&'/-]+", description):
        flash("Description contains invalid characters.")
        return redirect(url_for("main.trip_page", code=code))

    if len(description) > 100:
        flash("Description cannot exceed 100 characters.")
        return redirect(url_for("main.trip_page", code=code))

    if description.isdigit():
        flash("Description cannot contain only numbers.")
        return redirect(url_for("main.trip_page", code=code))
    
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
    db.session.flush()

    share=amount / len(split_among)
    for user in split_among:
        expense_split = ExpenseSplit(expense_id=expense.id, participant_id=int(user), share_amount=share)
        db.session.add(expense_split)

    db.session.commit()
    return redirect(url_for('main.trip_page', code=code))


@main.route('/trip/<code>/expense/<expense_id>/delete', methods=["POST"]) 
def delete_expense(code, expense_id):
    expense = Expense.query.filter_by(id=expense_id).first_or_404()
    trip = Trip.query.filter_by(code=code).first_or_404()

    if trip.expires_at < datetime.now():
            flash("Trip Expired!")
            return redirect(url_for('main.home'))

    if expense.trip_id != trip.id:
        abort(404)

    current_member = Participant.query.filter_by(trip_id=trip.id, session_token=session.get('trip_tokens', {}).get(trip.code)).first()

    if current_member is None or expense.paid_by != current_member.id:
        abort(403)

    ExpenseSplit.query.filter_by(expense_id=expense.id).delete()
    db.session.delete(expense)
    db.session.commit()

    return redirect(url_for('main.trip_page', code=expense.trip.code))


@main.route('/trip/<code>/expense/<expense_id>/edit', methods=["POST"])
def edit_expense(code, expense_id):
    trip = Trip.query.filter_by(code=code).first_or_404()
    expense = Expense.query.filter_by(id=expense_id).first_or_404()

    if trip.expires_at < datetime.now():
            flash("Trip Expired!")
            return redirect(url_for('main.home'))

    if expense.trip_id != trip.id:
        abort(404)
    
    session_token = session.get('trip_tokens', {}).get(trip.code)

    current_member = Participant.query.filter_by(trip_id=trip.id, session_token=session_token).first()

    if not current_member:
        flash("Please join the trip first.")
        return redirect(url_for('main.join_trip', code=trip.code))
    
    if expense.paid_by != current_member.id:
        flash("You can only edit your own expenses.")
        return redirect(url_for('main.trip_page', code=trip.code))
    
    description = request.form['description'].strip()

    if not description:
            flash("Description cannot be empty.")
            return redirect(url_for('main.trip_page', code=trip.code))

    if not re.fullmatch(r"[A-Za-z0-9\s.,()&'/-]+", description):
        flash("Description contains invalid characters.")
        return redirect(url_for("main.trip_page", code=code))

    if len(description) > 100:
        flash("Description cannot exceed 100 characters.")
        return redirect(url_for("main.trip_page", code=code))

    if description.isdigit():
        flash("Description cannot contain only numbers.")
        return redirect(url_for("main.trip_page", code=code))
    
    amount = float(request.form['amount'])
    split_among = request.form.getlist('split_among')
    
    if amount <= 0:
        flash("Amount must be greater than zero")
        return redirect(url_for('main.trip_page', code=trip.code))
    
    if not split_among:
        flash("Select atleast one participant.")
        return redirect(url_for('main.trip_page', code=trip.code))
    
    valid_ids = {
        str(participant.id)
        for participant in trip.participants
        }
    
    for participant_id in split_among:
        if participant_id not in valid_ids:
            abort(400)

    expense.description = description
    expense.amount = amount

    ExpenseSplit.query.filter_by(expense_id=expense.id).delete()

    share = amount / len(split_among)

    for participant_id in split_among:
        split = ExpenseSplit(expense_id=expense.id, participant_id=participant_id, share_amount=share)
        db.session.add(split)

    db.session.commit()
    flash("Expense updated successfully.")
    return redirect(url_for('main.trip_page', code=trip.code))
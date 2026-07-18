from models import db, Expense, ExpenseSplit
from sqlalchemy import func
def calculate_settlements(participants):
    creditors = []
    debtors = []
    
    for member in participants:
        total_paid = db.session.query(func.sum(Expense.amount)).filter(Expense.paid_by==member.id).scalar() or 0
        total_owed = db.session.query(func.sum(ExpenseSplit.share_amount)).filter(ExpenseSplit.participant_id==member.id).scalar() or 0
        net_balance = total_paid - total_owed
        if net_balance > 0:
            creditors.append([member.id, member.name, net_balance])
        else:
            debtors.append([member.id, member.name, abs(net_balance)])

    creditors.sort(key=lambda x : x[2], reverse=True)
    debtors.sort(key=lambda x : x[2], reverse=True)

    settlements = []
    while creditors and debtors:
        settled_amount = min(creditors[0][2], debtors[0][2])
        settlements.append({'from' : debtors[0][1], 
                            'to' : creditors[0][1],
                            'amount' : settled_amount})
        creditors[0][2] -= settled_amount
        debtors[0][2] -= settled_amount

        if creditors[0][2] == 0:
            creditors.pop(0)
        if debtors[0][2] == 0:
            debtors.pop(0)

    settlements.sort(key=lambda x: x['amount'], reverse=True)

    return settlements

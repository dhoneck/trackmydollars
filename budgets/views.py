from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseNotFound
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Sum
from django.contrib import messages
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from decimal import *
from .models import *
from functools import partial

# TODO: Integrate user accounts
# TODO: Add an add, update, and delete option on the income and expense budget item pages
# TODO: Add a "Back to Budget" button on each of the budget pages
# TODO: Add a transaction page

# General Views
def index(request):
    """ Redirects index view to dashboard """
    return HttpResponseRedirect('dashboard/')


def dashboard(request):
    """ Shows an overview of the user's account """
    # Sum Assets
    asset_total = 0
    for a in Asset.objects.all():
        if a.balances.first() is not None:
            asset_total += float(a.balances.first())

    # Sum Debt
    debt_total = 0
    for d in InstallmentDebt.objects.all():
        if d.balances.first() is not None:
            debt_total += float(d.balances.first())

    for d in RevolvingDebt.objects.all():
        if d.balances.first() is not None:
            debt_total += float(d.balances.first())

    # Calculate Net Worth
    net_worth_total = asset_total - debt_total

    # Get a list of abbreviated month names and a list of tuples containing year and month as strings ex: ('2020', '3')
    month_labels, year_month_labels = get_last_12_months_labels()
    print("Month Labels:", month_labels)
    print("Year Month Labels:", year_month_labels)

    # Convert year_month_labels into years and months list
    years = [year[0] for year in year_month_labels]
    months = [year[1] for year in year_month_labels]

    # Get a list of balances for assets, revolving debts, and installment debts for the last 12 months
    asset_partial = partial(get_last_12_months_data, obj=Asset, obj_bal=AssetBalance)
    asset_data = list(map(asset_partial, years, months))
    rev_debts_partial = partial(get_last_12_months_data, obj=RevolvingDebt, obj_bal=RevolvingDebtBalance)
    rev_debts_data = list(map(rev_debts_partial, years, months))
    inst_debts_partial = partial(get_last_12_months_data, obj=InstallmentDebt, obj_bal=InstallmentDebtBalance)
    inst_debts_data = list(map(inst_debts_partial, years, months))

    print(asset_data)
    print(rev_debts_data)
    print(inst_debts_data)

    debt_data = list(map(add_lists, rev_debts_data, inst_debts_data))
    net_worth_data = list(map(subtract_lists, asset_data, debt_data))
    debt_data_negative = [-d for d in debt_data]


    # TODO: Change the format spacing dynamically
    # TODO: Send the last 12 months of Net Worth Stats
    return render(request,
                  'budgets/dashboard.html',
                  {'asset_total': str("${: 14,.2f}".format(asset_total)),
                   'debt_total': str("${: 14,.2f}".format(debt_total)),
                   'net_worth_total': str("${: 14,.2f}".format(net_worth_total)),
                   'labels': month_labels,
                   'asset_data': asset_data,
                   'debt_data': debt_data_negative,
                   'net_worth_data': net_worth_data,
                   }
                  )


def add_lists(x, y):
    return x + y

def subtract_lists(x, y):
    return x - y

def get_last_12_months_labels():
    """Get a list of abbreviated month names and a list of tuples containing year and month as strings"""
    month_labels = []
    year_month_labels = []

    current_date = datetime.today()

    month = (current_date.strftime('%b %Y'))
    month_labels.append(month)

    year_month = (current_date.strftime('%Y'), current_date.strftime('%m').lstrip('0'))
    year_month_labels.append(year_month)

    for m in range(1, 12):
        adjusted_date = current_date+relativedelta(months=-m)
        if m == 11:  # Makes last month print the year as well
            month = adjusted_date.strftime('%b %Y')
        else:
            month = adjusted_date.strftime('%b')
        year_month = (adjusted_date.strftime('%Y'), adjusted_date.strftime('%m').lstrip('0'))
        month_labels.insert(0, month)
        year_month_labels.insert(0, year_month)

    return month_labels, year_month_labels


def get_last_12_months_data(year, month, obj, obj_bal):
    """Add up the balances for an object based on year and month"""
    total_for_month = Decimal(0.00)

    # Loop through all of the objects
    for a in obj.objects.all():
        print(f"Printing object {a}")

        filter_args = {}
        if issubclass(obj, Asset):
            # print('Asset Class!')
            filter_args['asset__id'] = a.id
        elif issubclass(obj, RevolvingDebt) or issubclass(obj, InstallmentDebt):
            # print('Revolving Debt Class!')
            filter_args['debt__id'] = a.id
        else:
            print('No class found!')

        filter_args['date__year'] = year
        filter_args['date__month'] = month

        print(filter_args)
        bal = obj_bal.objects.filter(**filter_args).first()
        print(obj_bal)
        print()
        print(f"{obj.__name__}, {obj_bal.__name__} ({year}, {month}) - {a.name} - {bal}")
        print(f"{a.name} Balance for {month}, {year} is {bal}")
        if bal != None:
            print(f"Adding {a.name} to the balance")
            total_for_month += bal.balance

        elif bal == None:  # Check for last balance entry
            # print('Printing ID', a.id)

            # kwargs
            kwargs = {"date__lt": date(int(year), int(month), 1)}
            if issubclass(obj, Asset):
                # print('Asset Class!')
                kwargs['asset_id'] = a.id
            elif issubclass(obj, RevolvingDebt):
                # print('Revolving Debt Class!')
                kwargs['debt_id'] = a.id
            elif issubclass(obj, InstallmentDebt):
                # print('Installment Debt Class!')
                kwargs['debt_id'] = a.id
            else:
                print('No class found!')


            remaining_balance = obj_bal.objects.filter(**kwargs).first()
            # print("Next Most Recent Balance:")
            # print(remaining_balance)
            if remaining_balance != None:
                total_for_month += remaining_balance.balance

    return float(total_for_month)

# def get_last_12_months_data(year, month):
#     asset_total_for_month = Decimal(0.00)
#     for a in Asset.objects.all():
#         print(f"\nCurrent asset: {a.name}")
#         asset_bal = AssetBalance.objects.filter(asset_id=a.id, date__year=year, date__month=month).first()
#         print(f"Asset Balance for {month}, {year} is {asset_bal}")
#         if asset_bal != None:
#             asset_total_for_month += asset_bal.balance
#
#         elif asset_bal == None:  # Check for last balance entry
#             remaining_balance = AssetBalance.objects.filter(
#                 asset_id=a.id,
#                 date__lt=date(int(year), int(month), 1)
#             ).first()
#             print("Next Most Recent Balance:")
#             print(remaining_balance)
#             if remaining_balance != None:
#                 asset_total_for_month += remaining_balance.balance
#
#     return float(asset_total_for_month)


# Asset Views
def assets_debts(request):
    # TODO: Calculate padding for net worth figures
    # TODO: Fix number alignment
    # TODO: Fix months to be abbreviated - e.g. March should be mar instead of March
    assets = Asset.objects.order_by('name')
    installment_debts = InstallmentDebt.objects.order_by('name')
    revolving_debts = RevolvingDebt.objects.order_by('name')

    # Net Worth Stats
    asset_total = 0
    for a in Asset.objects.all():
        if a.balances.first() is not None:
            asset_total += float(a.balances.first())
    #
    debt_total = 0
    for d in InstallmentDebt.objects.all():
        if d.balances.first() is not None:
            debt_total += float(d.balances.first())

    for d in RevolvingDebt.objects.all():
        if d.balances.first() is not None:
            debt_total += float(d.balances.first())

    net_worth_total = asset_total - debt_total

    return render(request,
                  'budgets/assets_debts.html',
                  {'assets': assets,
                   'installment_debts': installment_debts,
                   'revolving_debts': revolving_debts,
                   'asset_total': str("${: 12,.2f}".format(asset_total)),
                   'debt_total': str("${: 12,.2f}".format(debt_total)),
                   'net_worth_total': str("${: 12,.2f}".format(net_worth_total))}
                  )


class AddAsset(SuccessMessageMixin, CreateView):
    model = Asset
    fields = '__all__'
    template_name = 'budgets/add_asset.html'
    success_url = '../assets-debts'
    success_message = 'Asset successfully added!'


class UpdateAsset(SuccessMessageMixin, UpdateView):
    model = Asset
    fields = '__all__'
    template_name = 'budgets/update_asset.html'
    success_url = '../view'
    pk_url_kwarg = 'id'
    success_message = 'Asset successfully updated!'


def view_asset_details(request, id):
    context = {}
    try:
        context['asset'] = Asset.objects.get(id=id)
    except Asset.DoesNotExist:
        return HttpResponseNotFound("Page not found!")
    return render(request, 'budgets/view_asset.html', context)


class DeleteAsset(SuccessMessageMixin, DeleteView):
    model = Asset
    template_name = 'budgets/delete_asset.html'
    success_url = '../../../'
    pk_url_kwarg = 'id'
    success_message = 'Asset successfully deleted!'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(DeleteAsset, self).delete(request, *args, **kwargs)


class AddAssetBalance(SuccessMessageMixin, CreateView):
    model = AssetBalance
    fields = '__all__'
    template_name = 'budgets/add_asset_balance.html'
    success_url = '../view'
    success_message = 'Asset balance successfully added!'

    def get_initial(self):
        return {'asset': self.request.get_full_path().split('/')[-3],
                'date': datetime.today().strftime("%Y-%m-%d"),
                }


class UpdateAssetBalance(SuccessMessageMixin, UpdateView):
    model = AssetBalance
    fields = '__all__'
    template_name = 'budgets/update_asset_balance.html'
    success_url = '../view'
    pk_url_kwarg = 'bid'
    success_message = 'Asset balance successfully updated!'


class DeleteAssetBalance(SuccessMessageMixin, DeleteView):
    model = AssetBalance
    template_name = 'budgets/delete_asset_balance.html'
    success_url = '../view'
    pk_url_kwarg = 'bid'
    success_message = 'Asset balance successfully deleted!'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(DeleteAssetBalance, self).delete(request, *args, **kwargs)


# Debt Views
class AddInstallmentDebt(SuccessMessageMixin, CreateView):
    model = InstallmentDebt
    fields = '__all__'
    template_name = 'budgets/add_installment_debt.html'
    success_url = '../assets-debts'
    success_message = 'Installment debt successfully added!'


class AddInstallmentDebtBalance(SuccessMessageMixin, CreateView):
    model = InstallmentDebtBalance
    fields = '__all__'
    template_name = 'budgets/add_installment_debt_balance.html'
    success_url = '../assets-debts'
    success_message = 'Installment debt successfully added!'


class AddRevolvingDebt(SuccessMessageMixin, CreateView):
    model = RevolvingDebt
    fields = '__all__'
    template_name = 'budgets/add_revolving_debt_balance.html'
    success_url = '../assets-debts'
    success_message = 'Revolving debt successfully added!'


class AddRevolvingDebtBalance(SuccessMessageMixin, CreateView):
    model = RevolvingDebtBalance
    fields = '__all__'
    template_name = 'budgets/add_revolving_debt_balance.html'
    success_url = '../view'
    success_message = 'Debt balance successfully added!'

    def get_initial(self):
        return {'debt': self.request.get_full_path().split('/')[-3],
                'date': datetime.today().strftime("%Y-%m-%d"),
                }


class UpdateInstallmentDebt(SuccessMessageMixin, UpdateView):
    model = InstallmentDebt
    fields = '__all__'
    template_name = 'budgets/update_installment_debt.html'
    success_url = '../view'
    pk_url_kwarg = 'id'
    success_message = 'Installment debt successfully updated!'


class DeleteInstallmentDebt(SuccessMessageMixin, DeleteView):
    model = InstallmentDebt
    template_name = 'budgets/delete_installment_debt.html'
    success_url = '../../../'
    pk_url_kwarg = 'id'
    success_message = 'Installment debt successfully deleted!'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(DeleteInstallmentDebt, self).delete(request, *args, **kwargs)


class UpdateRevolvingDebt(SuccessMessageMixin, UpdateView):
    model = RevolvingDebt
    fields = '__all__'
    template_name = 'budgets/update_revolving_debt.html'
    success_url = '../view'
    pk_url_kwarg = 'id'
    success_message = 'Revolving debt successfully updated!'


class DeleteRevolvingDebt(SuccessMessageMixin, DeleteView):
    model = RevolvingDebt
    template_name = 'budgets/delete_revolving_debt.html'
    success_url = '../../../'
    pk_url_kwarg = 'id'
    success_message = 'Revolving debt successfully deleted!'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(DeleteRevolvingDebt, self).delete(request, *args, **kwargs)


class AddInstallmentDebtBalance(SuccessMessageMixin, CreateView):
    model = InstallmentDebtBalance
    fields = '__all__'
    template_name = 'budgets/add_installment_debt_balance.html'
    success_url = '../view'
    success_message = 'Debt balance successfully added!'

    def get_initial(self):
        return {'debt': self.request.get_full_path().split('/')[-3],
                'date': datetime.today().strftime("%Y-%m-%d"),
                }


class UpdateInstallmentDebtBalance(SuccessMessageMixin, UpdateView):
    model = InstallmentDebtBalance
    fields = '__all__'
    template_name = 'budgets/update_installment_debt_balance.html'
    success_url = '../view'
    pk_url_kwarg = 'bid'
    success_message = 'Debt balance successfully updated!'


class DeleteInstallmentDebtBalance(SuccessMessageMixin, DeleteView):
    model = InstallmentDebtBalance
    template_name = 'budgets/delete_installment_debt_balance.html'
    success_url = '../view'
    pk_url_kwarg = 'bid'
    success_message = 'Debt balance successfully deleted!'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(DeleteInstallmentDebtBalance, self).delete(request, *args, **kwargs)


class UpdateRevolvingDebtBalance(SuccessMessageMixin, UpdateView):
    model = RevolvingDebtBalance
    fields = '__all__'
    template_name = 'budgets/update_revolving_debt_balance.html'
    success_url = '../view'
    pk_url_kwarg = 'bid'
    success_message = 'Debt balance successfully updated!'


# New Classes as of 3-14-21
class UpdateIncomeBudgetItem(SuccessMessageMixin, UpdateView):
    model = IncomeBudgetItem
    fields = '__all__'
    template_name = 'budgets/update_income_budget_item.html'
    success_url = '../../'
    pk_url_kwarg = 'ibiid'
    success_message = 'Income budget item successfully updated!'


class DeleteIncomeBudgetItem(SuccessMessageMixin, DeleteView):
    model = IncomeBudgetItem
    template_name = 'budgets/delete_income_budget_item.html'
    success_url = '../../'
    pk_url_kwarg = 'ibiid'
    success_message = 'Income budget item successfully deleted!'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(DeleteIncomeBudgetItem, self).delete(request, *args, **kwargs)


class UpdateIncomeTransaction(SuccessMessageMixin, UpdateView):
    model = IncomeTransaction
    fields = '__all__'
    template_name = 'budgets/update_income_transaction.html'
    success_url = '../../view'
    pk_url_kwarg = 'itid'
    success_message = 'Income transaction successfully updated!'


class DeleteIncomeTransaction(SuccessMessageMixin, DeleteView):
    model = IncomeTransaction
    template_name = 'budgets/delete_income_transaction.html'
    success_url = '../../view'
    pk_url_kwarg = 'itid'
    success_message = 'Income transaction successfully deleted!'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(DeleteIncomeTransaction, self).delete(request, *args, **kwargs)


class UpdateExpenseCategory(SuccessMessageMixin, UpdateView):
    model = IncomeTransaction
    fields = '__all__'
    template_name = 'budgets/update_expense_category.html'
    success_url = '../../'
    pk_url_kwarg = 'ecid'
    success_message = 'Expense category successfully updated!'


class DeleteExpenseCategory(SuccessMessageMixin, DeleteView):
    model = ExpenseCategory
    template_name = 'budgets/delete_expense_category.html'
    success_url = '../../'
    pk_url_kwarg = 'ecid'
    success_message = 'Expense category successfully deleted!'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(DeleteExpenseCategory, self).delete(request, *args, **kwargs)


class UpdateExpenseBudgetItem(SuccessMessageMixin, UpdateView):
    model = ExpenseBudgetItem
    fields = '__all__'
    template_name = 'budgets/update_expense_budget_item.html'
    success_url = '../../../../'
    pk_url_kwarg = 'ebiid'
    success_message = 'Expense budget item successfully updated!'


class DeleteExpenseBudgetItem(SuccessMessageMixin, DeleteView):
    model = ExpenseBudgetItem
    template_name = 'budgets/delete_expense_budget_item.html'
    success_url = '../../../../'
    pk_url_kwarg = 'ebiid'
    success_message = 'Expense budget item successfully deleted!'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(DeleteExpenseBudgetItem, self).delete(request, *args, **kwargs)


class UpdateExpenseTransaction(SuccessMessageMixin, UpdateView):
    model = ExpenseTransaction
    fields = '__all__'
    template_name = 'budgets/update_expense_transaction.html'
    success_url = '../../view'
    pk_url_kwarg = 'etid'
    success_message = 'Expense transaction item successfully updated!'


class DeleteExpenseTransaction(SuccessMessageMixin, DeleteView):
    model = ExpenseTransaction
    template_name = 'budgets/delete_expense_transaction.html'
    success_url = '../../view'
    pk_url_kwarg = 'etid'
    success_message = 'Expense transaction item successfully deleted!'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(DeleteExpenseTransaction, self).delete(request, *args, **kwargs)


class DeleteRevolvingDebtBalance(SuccessMessageMixin, DeleteView):
    model = RevolvingDebtBalance
    template_name = 'budgets/delete_revolving_debt_balance.html'
    success_url = '../view'
    pk_url_kwarg = 'bid'
    success_message = 'Debt balance successfully deleted!'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(DeleteRevolvingDebtBalance, self).delete(request, *args, **kwargs)
#
#
def view_installment_debt_details(request, id):
    context = {}
    try:
        context['debt'] = InstallmentDebt.objects.get(id=id)
    except Debt.DoesNotExist:
        return HttpResponseNotFound("Page not found!")
    return render(request, 'budgets/view_installment_debt.html', context)


def view_revolving_debt_details(request, id):
    context = {}
    try:
        context['debt'] = RevolvingDebt.objects.get(id=id)
    except Debt.DoesNotExist:
        return HttpResponseNotFound("Page not found!")
    return render(request, 'budgets/view_revolving_debt.html', context)


# Add Budget Views
def budget(request):
    # Get current month and year to pass onto another view as a default
    current_month = datetime.today().strftime('%B').lower()
    current_year = datetime.today().year
    print(current_month)
    print(current_year)
    return HttpResponseRedirect(f'{current_month}/{current_year}')


class AddBudget(SuccessMessageMixin, CreateView):
    model = BudgetPeriod
    fields = '__all__'
    template_name = 'budgets/add_budget.html'
    success_url = '../'
    success_message = 'Budget successfully added!'

    def get_initial(self):
        split_url = self.request.get_full_path().split('/')
        month = datetime.strptime(split_url[-4], '%B').month
        year = split_url[-3]
        print(month)
        print(year)
        return {'month': month, 'year': year}

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        split_url = self.request.get_full_path().split('/')
        month = split_url[-4]
        year = split_url[-3]
        print(month)
        print(type(month))
        context['month'] = month.capitalize()
        context['year'] = year
        return context

def specific_budget(request, month, year):
    """ Shows a breakdown of monthly budget """
    # TODO: Get the received field to work - total the actual income and savings
    try:
        datetime_object = datetime.strptime(month, '%B')
        month_by_num = datetime_object.month
        bp = BudgetPeriod.objects.get(month=month_by_num, year=year)

        total_planned_income = Decimal(0.00)
        total_planned_expenses = Decimal(0.00)
        total_actual_income = Decimal(0.00)
        total_actual_expenses = Decimal(0.00)
        total_old_debt = Decimal(0.00)
        total_new_debt = Decimal(0.00)
        total_paid_debt = Decimal(0.00)
        total_remaining_new_debt = Decimal(0.00)
        total_remaining_old_debt = Decimal(0.00)
        total_remaining_debt = Decimal(0.00)
        print('Printing income budget items')
        for item in bp.income_budget_items.all():
            # print(item)
            # print(item.income_transactions.all())
            total_planned_income += item.planned_amount
            # Total income transactions
            for t in item.income_transactions.all():
                total_actual_income += t.amount


        # Sum the planned expenses
        old_debt_paid = Decimal(0.00)
        expense_categories = bp.expense_categories.all()
        for category in expense_categories:
            for expense_budget_item in category.expense_budget_items.all():
                if expense_budget_item.credit_debt == True:
                    total_old_debt += expense_budget_item.planned_amount
                total_planned_expenses += expense_budget_item.planned_amount
                for t in expense_budget_item.expense_transactions.all():

                    total_actual_expenses += t.amount
                    if t.credit_purchase:
                        total_new_debt += t.amount
                    if t.credit_payoff:
                        old_debt_paid += t.amount
                        total_paid_debt += t.amount
        total_remaining_old_debt = total_old_debt - old_debt_paid
        total_remaining_new_debt = total_new_debt  # TODO: Fix new debt payoff

    except BudgetPeriod.DoesNotExist:
        print('Does not exist, dummy')
        return HttpResponseRedirect('add-budget/')
    except:
        print('Second except clause')
        return HttpResponseNotFound("Page not found!")

    left_to_plan = total_planned_income - total_planned_expenses
    left_to_spend = total_actual_income - total_actual_expenses
    total_remaining_debt = total_old_debt + total_new_debt - total_paid_debt

    return render(request,
                  'budgets/budget.html',
                  {
                   'month': month.capitalize(),
                   'year': year,
                   'income_budget_items': bp.income_budget_items.all(),
                   'expense_categories': bp.expense_categories.all(),
                   'total_planned_income': total_planned_income,
                   'total_planned_expenses': total_planned_expenses,
                   'total_actual_income': total_actual_income,
                   'total_actual_expenses': total_actual_expenses,
                   'total_old_debt': total_old_debt,
                   'total_new_debt': total_new_debt,
                   'total_paid_debt': total_paid_debt,
                   'total_remaining_new_debt': total_remaining_new_debt,
                   'total_remaining_old_debt': total_remaining_old_debt,
                   'total_remaining_debt': total_remaining_debt,
                   'left_to_plan': left_to_plan,
                   'left_to_spend': left_to_spend,
                   'bp_id': bp.id
                  }
                  )

def change_budget(request, month, year):
    month = datetime.strptime(month, '%B').month
    current_budget = datetime(day=1, month=month, year=year)

    split_url = request.get_full_path().split("/")
    if split_url[-1] == "next":
        adjusted_date = current_budget+relativedelta(months=+1)
    elif split_url[-1] == "previous":
        adjusted_date = current_budget+relativedelta(months=-1)

    adjusted_month = adjusted_date.strftime("%B")
    adjusted_year = adjusted_date.year
    print(adjusted_month, adjusted_year)

    return HttpResponseRedirect(f'../../{adjusted_month}/{adjusted_year}')


def view_income_budget_item(request, month, year, ibiid):
    context = {}
    try:
        context['income_budget_item'] = IncomeBudgetItem.objects.get(id=ibiid)
    except IncomeBudgetItem.DoesNotExist:
        return HttpResponseNotFound("Page not found!")
    return render(request, 'budgets/view_income_budget_item.html', context)

def view_expense_budget_item(request, month, year, ecid, ebiid):
    context = {}
    try:
        context['expense_budget_item'] = ExpenseBudgetItem.objects.get(id=ebiid)
    except ExpenseBudgetItem.DoesNotExist:
        return HttpResponseNotFound("Page not found!")
    return render(request, 'budgets/view_expense_budget_item.html', context)


class AddIncomeBudgetItem(SuccessMessageMixin, CreateView):
    model = IncomeBudgetItem
    fields = '__all__'
    template_name = 'budgets/add_income_budget_item.html'
    success_url = './'
    success_message = 'Income budget item successfully added!'

    def get_initial(self):
        bpid = None
        try:
            m = datetime.strptime(self.request.get_full_path().split('/')[-3], '%B').month
            bpid = BudgetPeriod.objects.get(month=m, year=int(self.request.get_full_path().split('/')[-2]))
            print(bpid)
            # print(m)
        except:
            print('In except clause')
        print(self.request.get_full_path().split('/')[-2])
        print(self.request.get_full_path().split('/')[-3],)
        return {'budget_period': bpid,
                }


class AddIncomeTransaction(SuccessMessageMixin, CreateView):
    print('AddingIncomeTransaction')
    model = IncomeTransaction
    fields = '__all__'
    template_name = 'budgets/add_income_transaction.html'
    success_message = 'Income transaction successfully added!'

    def get_success_url(self):
        if 'back_to_item_view' in self.request.POST:
            return './view'
        else:
            return '../../'

    def get_initial(self):
        return {'budget_item': self.request.get_full_path().split('/')[-2],
                'date': datetime.today(),
                }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.META.get('HTTP_REFERER').split('/')[-1] == 'view':
            context['destination'] = 'back_to_item_view'
        else:
            context['destination'] = 'back_to_budget_view'
        return context




class AddExpenseCategory(SuccessMessageMixin, CreateView):
    model = ExpenseCategory
    fields = '__all__'
    template_name = 'budgets/add_expense_category.html'
    success_url = './'
    success_message = 'Expense category successfully added!'

    def get_initial(self):
        bpid = None
        try:
            split_url = self.request.get_full_path().split('/')
            print(split_url)
            month = datetime.strptime(split_url[-3], '%B').month
            print(month)
            year = split_url[-2]
            print(month, year)
            bpid = BudgetPeriod.objects.get(month=month, year=year)
            print(bpid)
            # print(m)
        except:
            print('In except clause')
        return {'budget_period': bpid,}


# TODO: Look this over, success url may need to be modified
class AddExpenseTransaction(SuccessMessageMixin, CreateView):
    model = ExpenseTransaction
    fields = '__all__'
    template_name = 'budgets/add_expense_transaction.html'
    success_url = '../../../../'
    success_message = 'Expense transaction successfully added!'

    def get_initial(self):
        # TODO: Make sure foreign key 'Budget Item' only shows that months items
        return {'expense_budget_item': self.request.get_full_path().split('/')[-2],
                'date': datetime.today(),
                }

    def get_success_url(self):
        if 'back_to_item_view' in self.request.POST:
            return './view'
        else:
            return '../../../../'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.META.get('HTTP_REFERER').split('/')[-1] == 'view':
            context['destination'] = 'back_to_item_view'
        else:
            context['destination'] = 'back_to_budget_view'
        return context



class AddExpenseBudgetItem(SuccessMessageMixin, CreateView):
    # TODO: Only show expense categories in that budget period
    model = ExpenseBudgetItem
    fields = '__all__'
    template_name = 'budgets/add_expense_budget_item.html'
    success_url = '../../'
    success_message = 'Expense budget item successfully added!'

    def get_initial(self):
        ecid = self.request.get_full_path().split('/')[-2]
        return {'expense_category': ecid,
                }

class DeleteBudget(SuccessMessageMixin, DeleteView):
    model = BudgetPeriod
    template_name = 'budgets/delete_budget.html'
    success_url = '/budget/'
    pk_url_kwarg = 'id'
    success_message = 'Budget successfully deleted!'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(DeleteBudget, self).delete(request, *args, **kwargs)

def view_transactions(request, month, year):
    print('Viewing transactions')
    datetime_object = datetime.strptime(month, '%B')
    month_by_num = datetime_object.month
    bp = BudgetPeriod.objects.get(month=month_by_num, year=year)

    print(bp)
    context = {}
    try:
        context['income_budget_items'] = IncomeBudgetItem.objects.filter(budget_period=bp.id)
        context['expense_categories'] = ExpenseCategory.objects.filter(budget_period=bp.id)
    except IncomeBudgetItem.DoesNotExist or ExpenseCategory.DoesNotExist:
        return HttpResponseNotFound("Page not found!")
    context['month'] = month.capitalize()
    context['year'] = year

    return render(request, 'budgets/view_transactions.html', context)


# # Schedule Views
# def schedule(request):
#     # Get current month and year to pass onto another view as a default
#     current_month = datetime.now().strftime('%B').lower()
#     current_year = datetime.now().year
#     return HttpResponseRedirect(f'{current_month}/{current_year}')
#
#
# def specific_schedule(request, month, year):
#     # Check to make sure the month URL parameter is valid
#     month = month.lower()
#     if month != 'january' and month != 'february' and month != 'march' and month != 'april' and month != 'may' and \
#             month != 'june' and month != 'july' and month != 'august' and month != 'september' and month != 'october' and \
#             month != 'november' and month != 'december':
#         return HttpResponseNotFound('Page not found')
#     # TODO: add code to check for month abbreviations or month number (e.g. jan, feb, mar, 1, 2, 3, etc)
#
#     budget_items = BudgetItem.objects.order_by('date')
#     abbr_month = month[0:3].capitalize()
#     print(abbr_month)
#     abbr_to_num = {name: num for num, name in enumerate(calendar.month_abbr) if num}
#     cm = abbr_to_num[abbr_month]
#     print(cm)
#     budget_items = BudgetItem.objects.filter(date__month=cm).order_by('date')
#     return render(request, 'budgets/specific_schedule.html', {'budget_items': budget_items,
#                                                               'month': month.capitalize(),
#                                                               'year': year
#                                                                 })
#
#
# def schedule_add_item(request):
#     if request.method == 'POST':
#         form = BudgetItemForm(request.POST)
#         if form.is_valid():
#             form.save()
#             messages.add_message(request, messages.INFO, 'Item was created successfully.')
#             return HttpResponseRedirect('../')
#     else:
#         form = BudgetItemForm()
#     return render(request, 'budgets/schedule_add_item.html', {'form': form})
#
#
# def schedule_edit_item(request, id):
#     return render(request, 'budgets/schedule_edit_item.html', {'id': id})
#
# def transactions(request):
#     return render(request, 'budgets/transactions.html')
# Report Views
# def reports(request):
#     return render(request, 'budgets/reports.html')

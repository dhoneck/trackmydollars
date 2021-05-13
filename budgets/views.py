from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseNotFound
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Sum, Count
from django.contrib import messages
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from decimal import *
from .models import *
from functools import partial
from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.urls import reverse
from budgets.forms import CustomUserCreationForm
from django.contrib.auth.decorators import login_required

# TODO: Get users to sign in by email
# TODO: Prevent users from being able to access each other's data
# TODO: Add a transaction page
# TODO: Add a template budget page and functionality
# TODO: Allow users to delete expense categories
# TODO: Implement money schedule imports into budget
# TODO: Figure out old and new debt in budget


# General Views
def index(request):
    """ Redirects index view to dashboard """
    if request.user.is_authenticated:
        return render(request, 'budgets/dashboard.html')
    else:
        return redirect('accounts/login/')


def about(request):
    """ An about page describing the service """
    return render(request, 'standard/about.html',)


def contact(request):
    """ A contact page for customer support or other feedback """
    return render(request, 'standard/contact.html',)


# Registration Views
def register(request):
    """ User registration page """
    if request.method == "GET":
        return render(
            request, "registration/register.html",
            {"form": CustomUserCreationForm}
        )
    elif request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(reverse("dashboard"))


# User Based Views
@login_required(login_url='../accounts/login/')
def dashboard(request):
    """ Shows an overview of the user's account """
    # Sum Assets
    asset_total = Decimal(0.00)
    for a in Asset.objects.filter(user=request.user.id):
        if a.balances.first() is not None:
            asset_total += a.balances.first().balance

    # Sum Debts
    debt_total = Decimal(0.00)
    for d in InstallmentDebt.objects.filter(user=request.user.id):
        if d.balances.first() is not None:
            debt_total += d.balances.first().balance

    for d in RevolvingDebt.objects.filter(user=request.user.id):
        if d.balances.first() is not None:
            debt_total += d.balances.first().balance

    # Calculate Net Worth
    net_worth_total = asset_total - debt_total

    # Get a list of abbreviated month names and a list of tuples containing year and month as strings ex: ('2020', '3')
    month_labels, year_month_labels = get_last_12_months_labels()
    # print('MONTH LABELS:', month_labels)
    # print('YEAR MONTH LABELS:', year_month_labels)

    # Convert year_month_labels into years and months list
    years = [year[0] for year in year_month_labels]
    months = [year[1] for year in year_month_labels]
    # print('YEARS:', years)
    # print('MONTHS:', months)

    # Get a list of balances for assets, revolving debts, and installment debts for the last 12 months
    asset_partial = partial(get_last_12_months_data, obj=Asset, obj_bal=AssetBalance, user=request.user.id)
    asset_data = list(map(asset_partial, years, months))
    rev_debts_partial = partial(get_last_12_months_data, obj=RevolvingDebt, obj_bal=RevolvingDebtBalance, user=request.user.id)
    rev_debts_data = list(map(rev_debts_partial, years, months))
    inst_debts_partial = partial(get_last_12_months_data, obj=InstallmentDebt, obj_bal=InstallmentDebtBalance, user=request.user.id)
    inst_debts_data = list(map(inst_debts_partial, years, months))

    debt_data = list(map(add_lists, rev_debts_data, inst_debts_data))
    net_worth_data = list(map(subtract_lists, asset_data, debt_data))
    debt_data_negative = [-d for d in debt_data]

    formatted_totals = format_numbers(asset_total=asset_total,
                                      debt_total=debt_total,
                                      net_worth_total=net_worth_total)

    return render(request,
                  'budgets/dashboard.html',
                  {'asset_total': formatted_totals['asset_total'],
                   'debt_total': formatted_totals['debt_total'],
                   'net_worth_total': formatted_totals['net_worth_total'],
                   'labels': month_labels,
                   'asset_data': asset_data,
                   'debt_data': debt_data_negative,
                   'net_worth_data': net_worth_data,
                   }
                  )


def format_numbers(**kwargs):
    """Formats strings to the correct amount of spaces based on longest number"""
    # Get the length of the longest integral number
    max_integral_length = 0
    for value in kwargs.values():
        len_of_value = len(str(value).split('.')[0])
        if len_of_value > max_integral_length:
            max_integral_length = len_of_value

    # Calculate number of commas
    commas = 0
    if max_integral_length > 3:
        commas = max_integral_length//3

    # Add total length of formatted number
    full_length = max_integral_length + commas + 3

    # Format numbers based on longest length
    formatted_numbers = {}
    format_string = "$ {:" + str(full_length) + ",.2f}"
    for key, value in kwargs.items():
        formatted_numbers[key] = format_string.format(value)
    return formatted_numbers


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


def get_last_12_months_data(year, month, obj, obj_bal, user):
    """Add up the balances for an object based on year and month"""
    total_for_month = Decimal(0.00)

    # Loop through all of the objects
    for a in obj.objects.filter(user=user):

        filter_args = {}
        if issubclass(obj, Asset):
            filter_args['asset__id'] = a.id
        elif issubclass(obj, RevolvingDebt) or issubclass(obj, InstallmentDebt):
            filter_args['debt__id'] = a.id
        else:
            print('No class found!')

        filter_args['date__year'] = year
        filter_args['date__month'] = month

        bal = obj_bal.objects.filter(**filter_args).first()

        if bal is not None:
            total_for_month += bal.balance

        elif bal is None:  # Check for last balance entry
            # kwargs
            kwargs = {"date__lt": date(int(year), int(month), 1)}
            if issubclass(obj, Asset):
                kwargs['asset_id'] = a.id
            elif issubclass(obj, RevolvingDebt):
                kwargs['debt_id'] = a.id
            elif issubclass(obj, InstallmentDebt):
                kwargs['debt_id'] = a.id
            else:
                print('No class found!')

            remaining_balance = obj_bal.objects.filter(**kwargs).first()
            if remaining_balance is not None:
                total_for_month += remaining_balance.balance

    return float(total_for_month)


# Asset Views
@login_required(login_url='../accounts/login/')
def assets_debts(request):
    # TODO: Fix number alignment
    # TODO: Fix months to be abbreviated - e.g. March should be mar instead of March
    assets = Asset.objects.filter(user=request.user.id).order_by('name')
    installment_debts = InstallmentDebt.objects.filter(user=request.user.id).order_by('name')
    revolving_debts = RevolvingDebt.objects.filter(user=request.user.id).order_by('name')

    # Net Worth Stats
    asset_total = 0
    for a in assets:
        if a.balances.first() is not None:
            asset_total += float(a.balances.first())
    #
    debt_total = 0
    for d in installment_debts:
        if d.balances.first() is not None:
            debt_total += float(d.balances.first())

    for d in revolving_debts:
        if d.balances.first() is not None:
            debt_total += float(d.balances.first())

    net_worth_total = asset_total - debt_total

    formatted_totals = format_numbers(asset_total=asset_total,
                                      debt_total=debt_total,
                                      net_worth_total=net_worth_total)
    return render(request,
                  'budgets/assets_debts.html',
                  {'assets': assets,
                   'installment_debts': installment_debts,
                   'revolving_debts': revolving_debts,
                   'asset_total': formatted_totals['asset_total'],
                   'debt_total': formatted_totals['debt_total'],
                   'net_worth_total': formatted_totals['net_worth_total']}
                  )


# @login_required(login_url='../accounts/login/')
class AddAsset(SuccessMessageMixin, CreateView):
    # https://stackoverflow.com/questions/21652073/django-how-to-set-a-hidden-field-on-a-generic-create-view
    model = Asset
    fields = ['name', 'type']
    template_name = 'budgets/add_asset.html'
    success_url = '../assets-debts'
    success_message = 'Asset successfully added!'

    def form_valid(self, form):
        user = self.request.user
        form.instance.user = user
        return super(AddAsset, self).form_valid(form)


class UpdateAsset(SuccessMessageMixin, UpdateView):
    model = Asset
    fields = ['name', 'type']
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
    fields = ['asset', 'balance', 'date']
    template_name = 'budgets/add_asset_balance.html'
    success_url = '../view'
    success_message = 'Asset balance successfully added!'

    def get_initial(self):
        return {'asset': self.request.get_full_path().split('/')[-3],
                'date': datetime.today().strftime("%Y-%m-%d"),
                }

    def form_valid(self, form):
        user = self.request.user
        form.instance.user = user
        return super(AddAssetBalance, self).form_valid(form)

class UpdateAssetBalance(SuccessMessageMixin, UpdateView):
    model = AssetBalance
    fields = ['asset', 'balance', 'date']
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
    fields = ['name', 'type', 'initial_amount', 'interest_rate', 'minimum_payment', 'payoff_date', 'date_opened']
    template_name = 'budgets/add_installment_debt.html'
    success_url = '../assets-debts'
    success_message = 'Installment debt successfully added!'

    def form_valid(self, form):
        user = self.request.user
        form.instance.user = user
        return super(AddInstallmentDebt, self).form_valid(form)


class AddRevolvingDebt(SuccessMessageMixin, CreateView):
    model = RevolvingDebt
    fields = ['name', 'type', 'interest_rate', 'credit_limit', 'date_opened']
    template_name = 'budgets/add_revolving_debt.html'
    success_url = '../assets-debts'
    success_message = 'Revolving debt successfully added!'

    def form_valid(self, form):
        user = self.request.user
        form.instance.user = user
        return super(AddRevolvingDebt, self).form_valid(form)


class AddRevolvingDebtBalance(SuccessMessageMixin, CreateView):
    model = RevolvingDebtBalance
    fields = ['debt', 'balance', 'date',]
    template_name = 'budgets/add_revolving_debt_balance.html'
    success_url = '../view'
    success_message = 'Debt balance successfully added!'

    def get_initial(self):
        return {'debt': self.request.get_full_path().split('/')[-3],
                'date': datetime.today().strftime("%Y-%m-%d"),
                }

    def form_valid(self, form):
        user = self.request.user
        form.instance.user = user
        return super(AddRevolvingDebtBalance, self).form_valid(form)

class UpdateInstallmentDebt(SuccessMessageMixin, UpdateView):
    model = InstallmentDebt
    fields = ['name', 'type', 'interest_rate', 'date_opened', 'initial_amount', 'minimum_payment', 'payoff_date']
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
    fields = ['name', 'type', 'interest_rate', 'date_opened', 'credit_limit']
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
    fields = ['debt', 'balance', 'date']
    template_name = 'budgets/add_installment_debt_balance.html'
    success_url = '../view'
    success_message = 'Debt balance successfully added!'

    def get_initial(self):
        return {'debt': self.request.get_full_path().split('/')[-3],
                'date': datetime.today().strftime("%Y-%m-%d"),
                }

    def form_valid(self, form):
        user = self.request.user
        form.instance.user = user
        return super(AddInstallmentDebtBalance, self).form_valid(form)

class UpdateInstallmentDebtBalance(SuccessMessageMixin, UpdateView):
    model = InstallmentDebtBalance
    fields = ['debt', 'balance', 'date']
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
    fields = ['debt', 'balance', 'date']
    template_name = 'budgets/update_revolving_debt_balance.html'
    success_url = '../view'
    pk_url_kwarg = 'bid'
    success_message = 'Debt balance successfully updated!'


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
    fields = ['month', 'year', 'starting_bank_balance', 'add_money_schedule_items', 'use_last_budget']
    template_name = 'budgets/add_budget.html'
    success_url = '../'
    success_message = 'Budget successfully added!'

    def get_initial(self):
        split_url = self.request.get_full_path().split('/')
        month = datetime.strptime(split_url[-4], '%B').month
        year = split_url[-3]
        return {'month': month, 'year': year}

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        split_url = self.request.get_full_path().split('/')
        month = split_url[-4]
        year = split_url[-3]
        context['month'] = month.capitalize()
        context['year'] = year
        return context

    def form_valid(self, form):
        user = self.request.user
        form.instance.user = user
        return super(AddBudget, self).form_valid(form)


def specific_budget(request, month, year):
    """ Shows a breakdown of monthly budget """
    # TODO: Get the received field to work - total the actual income and savings
    try:
        datetime_object = datetime.strptime(month, '%B')
        month_by_num = datetime_object.month
        bp = BudgetPeriod.objects.get(user=request.user.id, month=month_by_num, year=year)

        total_planned_income = Decimal(0.00)
        total_planned_expenses = Decimal(0.00)
        total_actual_income = Decimal(0.00)
        total_actual_expenses = Decimal(0.00)
        total_old_debt = Decimal(0.00)
        total_new_debt = Decimal(0.00)
        total_paid_debt = Decimal(0.00)

        income_budget_items = bp.income_budget_items.all()

        ec = bp.expense_categories.filter(user=request.user.id),

        for item in income_budget_items:
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


    except BudgetPeriod.DoesNotExist:
        print('Does not exist, dummy')
        return HttpResponseRedirect('add-budget/')
    except Exception as err:
        print('Second except clause')
        return HttpResponseNotFound(f"Page not found! Here is the error: {err}")

    left_to_plan = total_planned_income - total_planned_expenses
    left_to_spend = total_actual_income - total_actual_expenses
    total_remaining_debt = total_new_debt - total_paid_debt

    return render(request,
                  'budgets/budget.html',
                  {
                   'month': month.capitalize(),
                   'year': year,
                   'income_budget_items': income_budget_items,
                   'expense_categories': bp.expense_categories.all(),
                   'total_planned_income': total_planned_income,
                   'total_planned_expenses': total_planned_expenses,
                   'total_actual_income': total_actual_income,
                   'total_actual_expenses': total_actual_expenses,
                   'total_new_debt': total_new_debt,
                   'total_paid_debt': total_paid_debt,
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
    fields = ['budget_period', 'name', 'planned_amount', 'transfer']
    template_name = 'budgets/add_income_budget_item.html'
    success_url = './'
    success_message = 'Income budget item successfully added!'

    def get_initial(self):
        bpid = None
        try:
            m = datetime.strptime(self.request.get_full_path().split('/')[-3], '%B').month
            bpid = BudgetPeriod.objects.get(user=self.request.user, month=m, year=int(self.request.get_full_path().split('/')[-2]))
            print(bpid)
            print(m)
        except:
            print('In except clause')
        print(self.request.get_full_path().split('/')[-2])
        print(self.request.get_full_path().split('/')[-3],)
        return {'budget_period': bpid,
                }

    def form_valid(self, form):
        user = self.request.user
        form.instance.user = user
        return super(AddIncomeBudgetItem, self).form_valid(form)


class AddIncomeTransaction(SuccessMessageMixin, CreateView):
    print('AddingIncomeTransaction')
    model = IncomeTransaction
    fields = ['budget_item', 'name', 'amount', 'date']
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

    def form_valid(self, form):
        user = self.request.user
        form.instance.user = user
        return super(AddIncomeTransaction, self).form_valid(form)

class AddExpenseCategory(SuccessMessageMixin, CreateView):
    model = ExpenseCategory
    fields = ['budget_period', 'name']
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
            bpid = BudgetPeriod.objects.get(user=self.request.user, month=month, year=year)
            print(bpid)
            # print(m)
        except:
            print('In except clause')
        return {'budget_period': bpid,}

    def form_valid(self, form):
        user = self.request.user
        form.instance.user = user
        return super(AddExpenseCategory, self).form_valid(form)

# TODO: Look this over, success url may need to be modified
class AddExpenseTransaction(SuccessMessageMixin, CreateView):
    model = ExpenseTransaction
    fields = ['expense_budget_item', 'name', 'amount', 'credit_purchase', 'credit_payoff', 'date']
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

    def form_valid(self, form):
        user = self.request.user
        form.instance.user = user
        return super(AddExpenseTransaction, self).form_valid(form)

class AddExpenseBudgetItem(SuccessMessageMixin, CreateView):
    # TODO: Only show expense categories in that budget period
    model = ExpenseBudgetItem
    fields = ['expense_category', 'name', 'planned_amount', 'transfer']
    template_name = 'budgets/add_expense_budget_item.html'
    success_url = '../../'
    success_message = 'Expense budget item successfully added!'

    def get_initial(self):
        ecid = self.request.get_full_path().split('/')[-2]
        return {'expense_category': ecid,
                }

    def form_valid(self, form):
        user = self.request.user
        form.instance.user = user
        return super(AddExpenseBudgetItem, self).form_valid(form)

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


# Schedule Views
def view_schedule(request):
    context = {}

    context['weekly'] = ScheduleItem.objects.filter(user=request.user.id, frequency='Weekly').order_by('first_due_date')
    context['every_two_weeks'] = ScheduleItem.objects.filter(user=request.user.id, frequency='Every two weeks').order_by('first_due_date')
    context['monthly'] = ScheduleItem.objects.filter(user=request.user.id, frequency='Monthly').order_by('first_due_date')
    context['every_two_months'] = ScheduleItem.objects.filter(user=request.user.id, frequency='Every two months').order_by('first_due_date')
    context['quarterly'] = ScheduleItem.objects.filter(user=request.user.id, frequency='Quarterly').order_by('first_due_date')
    context['every_six_months'] = ScheduleItem.objects.filter(user=request.user.id, frequency='Every six months').order_by('first_due_date')
    context['yearly'] = ScheduleItem.objects.filter(user=request.user.id, frequency='Yearly').order_by('first_due_date')
    context['one_time'] = ScheduleItem.objects.filter(user=request.user.id, frequency='One time only').order_by('first_due_date')

    yearly_amount = Decimal(0.00)

    totals = {}
    totals['weekly_total'] = (context['weekly'].aggregate(Sum('amount'))['amount__sum'] or 0) * 52
    totals['every_two_weeks_total'] = (context['every_two_weeks'].aggregate(Sum('amount'))['amount__sum'] or 0) * 26
    totals['monthly_total'] = (context['monthly'].aggregate(Sum('amount'))['amount__sum'] or 0) * 12
    totals['every_two_months_total'] = (context['every_two_months'].aggregate(Sum('amount'))['amount__sum'] or 0) * 6
    totals['quarterly_total'] = (context['quarterly'].aggregate(Sum('amount'))['amount__sum'] or 0) * 4
    totals['every_six_months_total'] = (context['every_six_months'].aggregate(Sum('amount'))['amount__sum'] or 0) * 2
    totals['yearly_total'] = (context['yearly'].aggregate(Sum('amount'))['amount__sum'] or 0) * 1
    totals['one_time_total'] = (context['one_time'].aggregate(Sum('amount'))['amount__sum'] or 0) * 1

    entire_total = Decimal(0.00)
    non_monthly_total = Decimal(0.00)

    for key, value in totals.items():
        if key != 'monthly_total':
            non_monthly_total += value
        entire_total += value

    totals['entire_total'] = "{:.2f}".format(entire_total)
    totals['non_monthly_total'] = "{:.2f}".format(non_monthly_total)

    totals['monthly_non_monthly_total'] = Decimal("{:.2f}".format(non_monthly_total / 12))

    context['totals'] = totals

    return render(request, 'schedule/view_schedule.html', context)


class AddScheduleItem(SuccessMessageMixin, CreateView):
    model = ScheduleItem
    fields = ['name', 'amount', 'category', 'first_due_date', 'frequency']
    template_name = 'schedule/add_schedule_item.html'
    success_url = '/schedule/'
    success_message = 'Schedule item successfully added!'

    def form_valid(self, form):
        user = self.request.user
        form.instance.user = user
        return super(AddScheduleItem, self).form_valid(form)

class UpdateScheduleItem(SuccessMessageMixin, UpdateView):
    model = ScheduleItem
    fields = ['name', 'amount', 'category', 'first_due_date', 'frequency']
    template_name = 'schedule/update_schedule_item.html'
    success_url = '/schedule/'
    pk_url_kwarg = 'siid'
    success_message = 'Schedule item successfully updated!'


class DeleteScheduleItem(SuccessMessageMixin, DeleteView):
    model = ScheduleItem
    template_name = 'schedule/delete_schedule_item.html'
    success_url = '/schedule/'
    pk_url_kwarg = 'siid'
    success_message = 'Schedule item successfully deleted!'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(DeleteScheduleItem, self).delete(request, *args, **kwargs)


# # Transactions Views
# def transactions(request):
#     return render(request, 'budgets/transactions.html')

# # Report Views
# def reports(request):
#     return render(request, 'budgets/reports.html')

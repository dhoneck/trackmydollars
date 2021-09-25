from django.http import HttpResponseRedirect, HttpResponse, HttpResponseNotFound
from django.views.generic.edit import CreateView, UpdateView, DeleteView, FormView
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Sum, Count
from django.contrib import messages
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from decimal import *
from .models import *
from django.db.models import F
from django.db import IntegrityError
from functools import partial
from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.urls import reverse
from budgets.forms import CustomUserCreationForm, BudgetPeriodForm, ExpenseTransactionForm, ExpenseTransactionDebtPaymentForm
from django.contrib.auth.decorators import login_required

# TODO: Add a template budget page and functionality
# TODO: Allow users to delete expense categories
# TODO: Implement money schedule imports into budget
# TODO: Figure out old and new debt in budget
# TODO: Add message script to each page - sometimes the message won't pop up until you go to a certain page
# TODO: Make date picker close after selection
# TODO: Fix table formatting - column spacing, alignment, currency
# TODO: Fix the errors when importing templates and money schedule items


# General Views
def index(request):
    """ Redirects user to login screen or dashboard based on current authentication status """
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
# TODO: Get users to sign in by email
# TODO: Prevent users from being able to access each other's data
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

# User settings views
#TODO: Add a user avatar next to their email
#TODO: Add user settings page
#TODO: Allow user to disable pages
#TODO: Allow user to disable checking account tracking
#TODO: Transfer In Item Name (e.g. Extra Funds) - for when automatic transfers happen such as 
#TODO: Transfer Out Category Name (e.g. Everything Else) - for when automatic transfers happen such as 
#TODO: Transfer Out Item Name (e.g. Reserved Funds)

# Helper Functions
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


def get_last_12_months_labels(get_next_12=False):
    """Get a list of abbreviated month names and a list of tuples containing year and month as strings"""
    month_labels = []
    year_month_labels = []

    current_date = datetime.today()

    # If get_next_12 is set to True it will set the current_date value 11 months ahead
    if get_next_12:
        current_date = current_date + relativedelta(months=11)

    month = (current_date.strftime('%b %Y'))
    month_labels.append(month)

    year_month = (current_date.strftime('%Y'), current_date.strftime('%m').lstrip('0'))
    year_month_labels.append(year_month)

    for m in range(1, 12):
        adjusted_date = current_date+relativedelta(months=-m)
        if m == 11:  # Makes last month include the year as well
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

            remaining_balance = obj_bal.objects.filter(**kwargs).first()
            if remaining_balance is not None:
                total_for_month += remaining_balance.balance

    return float(total_for_month)


# User Based Views
# TODO: Add content from your money schedule
# TODO: Add content from your budget
# TODO: Prevent future month assets and debt balances from showing up in current month
# TODO: Provide more options for viewing net worth (e.g. week, month, year, all time)
@login_required(login_url='../accounts/login/')
def dashboard(request):
    """ Shows an overview of the user's account """
    # TODO: Fix rounding issues for the net worth line - I see it has a rounding issue with too many decimals
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

    # Convert year_month_labels into years and months list
    years = [year[0] for year in year_month_labels]
    months = [year[1] for year in year_month_labels]

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
        form.instance.user = self.request.user
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


# TODO: Remove asset from the form and add it to the template
# TODO: Handle form when values are not unique
class AddAssetBalance(SuccessMessageMixin, CreateView):
    model = AssetBalance
    fields = ['balance', 'date']
    template_name = 'budgets/add_asset_balance.html'
    success_url = '../view'
    success_message = 'Asset balance successfully added!'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        asset_id = int(self.request.get_full_path().split('/')[-3])
        asset_name = Asset.objects.get(id=asset_id).name
        context['asset_name'] = asset_name
        return context

    def get_initial(self):
        return {'date': datetime.today().strftime("%Y-%m-%d")}

    def form_valid(self, form):
        try:
            form.instance.user = self.request.user
            form.instance.asset_id = int(self.request.get_full_path().split('/')[-3])
            return super(AddAssetBalance, self).form_valid(form)
        except IntegrityError:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    message=f'Your data has not been saved because there is already an entry for {form.instance.date}.',
                )
            )


class UpdateAssetBalance(SuccessMessageMixin, UpdateView):
    model = AssetBalance
    fields = ['balance', 'date']
    template_name = 'budgets/update_asset_balance.html'
    success_url = '../view'
    pk_url_kwarg = 'bid'
    success_message = 'Asset balance successfully updated!'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        asset_id = int(self.request.get_full_path().split('/')[-3])
        asset_name = Asset.objects.get(id=asset_id).name
        context['asset_name'] = asset_name
        return context

    def form_valid(self, form):
        try:
            return super(UpdateAssetBalance, self).form_valid(form)
        except IntegrityError:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    message=f'Your data has not been saved because there is already an entry for {form.instance.date}.',
                )
            )


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
    fields = ['name', 'type', 'initial_amount', 'interest_rate', 'minimum_payment', 'payoff_date']
    template_name = 'budgets/add_installment_debt.html'
    success_url = '../assets-debts'
    success_message = 'Installment debt successfully added!'

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super(AddInstallmentDebt, self).form_valid(form)


class AddRevolvingDebt(SuccessMessageMixin, CreateView):
    model = RevolvingDebt
    fields = ['name', 'type', 'interest_rate', 'credit_limit']
    template_name = 'budgets/add_revolving_debt.html'
    success_url = '../assets-debts'
    success_message = 'Revolving debt successfully added!'

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super(AddRevolvingDebt, self).form_valid(form)


class AddRevolvingDebtBalance(SuccessMessageMixin, CreateView):
    model = RevolvingDebtBalance
    fields = ['balance', 'date',]
    template_name = 'budgets/add_revolving_debt_balance.html'
    success_url = '../view'
    success_message = 'Debt balance successfully added!'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        debt_id = int(self.request.get_full_path().split('/')[-3])
        debt_name = RevolvingDebt.objects.get(id=debt_id).name
        context['debt_name'] = debt_name
        return context

    def get_initial(self):
        return {'debt': self.request.get_full_path().split('/')[-3],
                'date': datetime.today().strftime("%Y-%m-%d"),
                }

    def form_valid(self, form):
        try:
            form.instance.user = self.request.user
            form.instance.debt_id = int(self.request.get_full_path().split('/')[-3])
            return super(AddRevolvingDebtBalance, self).form_valid(form)
        except IntegrityError:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    message=f'Your data has not been saved because there is already an entry for {form.instance.date}.',
                )
            )


class UpdateInstallmentDebt(SuccessMessageMixin, UpdateView):
    model = InstallmentDebt
    fields = ['name', 'type', 'initial_amount', 'interest_rate', 'minimum_payment', 'payoff_date']
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
    fields = ['name', 'type', 'interest_rate', 'credit_limit']
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
    fields = ['balance', 'date']
    template_name = 'budgets/add_installment_debt_balance.html'
    success_url = '../view'
    success_message = 'Debt balance successfully added!'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        debt_id = int(self.request.get_full_path().split('/')[-3])
        debt_name = InstallmentDebt.objects.get(id=debt_id).name
        context['debt_name'] = debt_name
        return context

    def get_initial(self):
        return {'debt': self.request.get_full_path().split('/')[-3],
                'date': datetime.today().strftime("%Y-%m-%d"),
                }

    def form_valid(self, form):
        try:
            form.instance.user = self.request.user
            form.instance.debt_id = int(self.request.get_full_path().split('/')[-3])
            return super(AddInstallmentDebtBalance, self).form_valid(form)
        except IntegrityError:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    message=f'Your data has not been saved because there is already an entry for {form.instance.date}.',
                )
            )


class UpdateInstallmentDebtBalance(SuccessMessageMixin, UpdateView):
    model = InstallmentDebtBalance
    fields = ['balance', 'date']
    template_name = 'budgets/update_installment_debt_balance.html'
    success_url = '../view'
    pk_url_kwarg = 'bid'
    success_message = 'Debt balance successfully updated!'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        debt_id = int(self.request.get_full_path().split('/')[-3])
        debt_name = InstallmentDebt.objects.get(id=debt_id).name
        context['debt_name'] = debt_name
        return context

    def form_valid(self, form):
        try:
            return super(UpdateInstallmentDebtBalance, self).form_valid(form)
        except IntegrityError:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    message=f'Your data has not been saved because there is already an entry for {form.instance.date}.',
                )
            )


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
    fields = ['balance', 'date']
    template_name = 'budgets/update_revolving_debt_balance.html'
    success_url = '../view'
    pk_url_kwarg = 'bid'
    success_message = 'Debt balance successfully updated!'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        debt_id = int(self.request.get_full_path().split('/')[-3])
        debt_name = RevolvingDebt.objects.get(id=debt_id).name
        context['debt_name'] = debt_name
        return context

    def form_valid(self, form):
        try:
            return super(UpdateRevolvingDebtBalance, self).form_valid(form)
        except IntegrityError:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    message=f'Your data has not been saved because there is already an entry for {form.instance.date}.',
                )
            )


class UpdateIncomeBudgetItem(SuccessMessageMixin, UpdateView):
    model = IncomeBudgetItem
    fields = ['name', 'planned_amount', 'type']
    template_name = 'budgets/update_income_budget_item.html'
    success_url = '../../'
    pk_url_kwarg = 'ibiid'
    success_message = 'Income budget item successfully updated!'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        month, year = get_month_and_year_from_request(self.request)
        user = self.request.user
        context['budget_period'] = get_budget_period(user, month, year)
        return context

    def form_valid(self, form):
        month, year = get_month_and_year_from_request(self.request)
        user = self.request.user
        form.instance.budget_period = get_budget_period(user, month, year)
        form.instance.user = user
        return super(UpdateIncomeBudgetItem, self).form_valid(form)


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
    fields = ['name', 'amount', 'date']
    template_name = 'budgets/update_income_transaction.html'
    success_url = '../../view'
    pk_url_kwarg = 'itid'
    success_message = 'Income transaction successfully updated!'

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.budget_item_id = self.request.get_full_path().split('/')[-4]
        return super(UpdateIncomeTransaction, self).form_valid(form)


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
    model = ExpenseCategory
    fields = ['name']
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
    fields = ['name', 'planned_amount', 'type']
    template_name = 'budgets/update_expense_budget_item.html'
    success_url = '../../../../'
    pk_url_kwarg = 'ebiid'
    success_message = 'Expense budget item successfully updated!'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['expense_category'] = ExpenseCategory.objects.get(id=self.request.get_full_path().split('/')[-4])
        except Exception as err:
            print('There was an error:', err)
            context['expense_category'] = None
        return context

    def form_valid(self, form):
        user = self.request.user
        form.instance.user = user
        form.instance.expense_category_id = self.request.get_full_path().split('/')[-4]
        return super(UpdateExpenseBudgetItem, self).form_valid(form)


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
    fields = ['name', 'amount', 'credit_purchase', 'date']
    template_name = 'budgets/update_expense_transaction.html'
    success_url = '../../view'
    pk_url_kwarg = 'etid'
    success_message = 'Expense transaction item successfully updated!'

    def form_valid(self, form):
        user = self.request.user
        form.instance.user = user
        form.instance.expense_budget_item_id = self.request.get_full_path().split('/')[-4]
        return super(UpdateExpenseTransaction, self).form_valid(form)


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


def get_month_and_year_from_request(request):
    split_url = request.get_full_path().split('/')
    month = split_url[2]
    year = split_url[3]
    return month, year


# Add Budget Views
def get_budget_period(user, month, year):
    month = str(month)  # Convert for testing
    bp = None

    try:
        if month.isalpha:  # Convert from alpha (e.g. july) to int (e.g. 7)
            datetime_object = datetime.strptime(month, '%B')
            month_by_num = datetime_object.month
        else:
            month_by_num = int(month)
        bp = BudgetPeriod.objects.get(user=user, month=month_by_num, year=year)
    except BudgetPeriod.DoesNotExist:
        raise BudgetPeriod.DoesNotExist
    except Exception as err:
        return HttpResponseNotFound(f"Page not found! Here is the error: {err} {type(err)}")
    return bp


def budget(request):
    # Get current month and year to pass onto another view as a default
    current_month = datetime.today().strftime('%B').lower()
    current_year = datetime.today().year
    return HttpResponseRedirect(f'{current_month}/{current_year}')


class AddBudgetPeriod(FormView, SuccessMessageMixin):
    template_name = 'budgets/add_budget.html'
    form_class = BudgetPeriodForm
    success_url = '../'
    success_message = 'Budget successfully added!'

    def get_form_kwargs(self):
        kwargs = super(AddBudgetPeriod, self).get_form_kwargs()
        kwargs.update({'user': self.request.user.id})
        return kwargs

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
        current_user = self.request.user.id
        form_year = form.cleaned_data['year']
        form_month = form.cleaned_data['month']
        form_sbb = form.cleaned_data['starting_bank_balance']

        try:
            # Create a new budget period
            BudgetPeriod(year=form_year, month=form_month, starting_bank_balance=form_sbb, user_id=current_user).save()

            # Retrieve the new budget period
            new_bp = BudgetPeriod.objects.get(year=form_year, month=form_month, user_id=current_user)

            # Check to see if there is a template budget period - if there is add those items to current budget
            template_bp = form.cleaned_data['template']
            if template_bp:
                # Add income budget items to the new budget period
                ibi = IncomeBudgetItem.objects.filter(budget_period_id=template_bp)
                for item in ibi:
                    item.pk = None
                    item.budget_period_id = new_bp.id
                    item.save()
                # Add expense categories and expense budget items to the new budget period
                ec = ExpenseCategory.objects.filter(budget_period_id=template_bp)
                for category in ec:
                    original_id = category.id
                    budget_items = category.expense_budget_items.all()
                    category.id = None
                    category.budget_period_id = new_bp.id
                    category.save()
                    new_id = category.id
                    for i in budget_items:
                        i.id = None
                        i.expense_category_id = new_id
                        i.save()

            usable_balance = form.cleaned_data['usable_balance']
            if usable_balance > 0:
                reserve_bi = IncomeBudgetItem(name='Reserve Funds', planned_amount=usable_balance, budget_period_id=new_bp.id, user_id=current_user, type='Reserve')
                reserve_bi.save()

            add_money_schedule_items = form.cleaned_data['add_money_schedule_items']

            # Check for current month's budget items
            items_for_month = []
            if add_money_schedule_items:
                # for item in ScheduleItem.objects.filter(user=self.request.user.id).exclude(frequency="Monthly"):
                for item in ScheduleItem.objects.filter(user=self.request.user.id):
                    match = item.monthly_occurrences(int(form_year), int(form_month))
                    if match:
                        items_for_month.append(item.monthly_occurrences(int(form_year), int(form_month)))

                # Add money schedule items to budget
                for item in items_for_month:
                    # Check if expense category already exists
                    expense_cat, cat_created = ExpenseCategory.objects.get_or_create(user_id=current_user, budget_period=new_bp, name=item[0].category)

                    expense_item, item_created = ExpenseBudgetItem.objects.get_or_create(
                        expense_category=expense_cat,
                        name=item[0].name,
                        planned_amount=item[0].amount,
                        user_id=item[0].user_id,
                    )

        except Exception as err:
            return HttpResponseNotFound(f"Page not found! Here is the error: {err} {type(err)}")
        return super(AddBudgetPeriod, self).form_valid(form)


class UpdateBudgetPeriod(SuccessMessageMixin, UpdateView):
    model = BudgetPeriod
    fields = ['starting_bank_balance']
    template_name = 'budgets/update_budget_period.html'
    success_url = '../'
    pk_url_kwarg = 'bp'
    success_message = 'Budget period successfully updated!'

# TODO: Add an add transaction button
# TODO: Add autofill
# TODO: Allow users to move categories and budget items
# TODO: Prevent users from being able to add reserve transactions - it should be automatically

def specific_budget(request, month, year):
    """ Shows a breakdown of monthly budget """
    try:
        bp = get_budget_period(user=request.user.id, month=month, year=year)

        total_planned_income = Decimal(0.00)
        total_planned_expenses = Decimal(0.00)
        total_actual_income = Decimal(0.00)
        total_actual_expenses = Decimal(0.00)
        total_old_debt = Decimal(0.00)
        total_new_debt = Decimal(0.00)
        total_paid_debt = Decimal(0.00)
        reserved_funds = Decimal(0.00)

        income_budget_items = bp.income_budget_items.all()

        all_transactions = []

        for item in income_budget_items:
            total_planned_income += item.planned_amount

            # Check if reserved funds
            if item.type == 'Reserve':
                total_actual_income += item.planned_amount
                reserved_funds += item.planned_amount

            # Total income transactions
            for t in item.income_transactions.all():
                total_actual_income += t.amount
                all_transactions.append(t)

        # Check the transactions for new debt and adjust if needed
        print('Transactions Filter Method')

        credit_expense_transactions = ExpenseTransaction.objects.filter(
            expense_budget_item__expense_category__budget_period=bp,
            credit_purchase=True
        )
        print(f'Sum {credit_expense_transactions.aggregate(Sum("amount"))}')
        cc_purchase_total = credit_expense_transactions.aggregate(Sum('amount'))['amount__sum'] or Decimal(0.00)

        new_debt_category = bp.expense_categories.filter(name='New Debt')
        print(f'New debt {new_debt_category}')

        if new_debt_category:
            print('New Debt Exists')
            new_debt_budget_item = new_debt_category[0].expense_budget_items.all()[0]

            if new_debt_budget_item.planned_amount == cc_purchase_total:
                print('Do nothing w/ new debt!')
            else:
                print('Modifying new debt!')
                new_debt_budget_item.planned_amount = cc_purchase_total
                if new_debt_budget_item.planned_amount == 0:
                    print('Planned amount is 0, remove New Debt')
                    new_debt_budget_item.expense_category.delete()
                else:
                    print('Planned amount is not 0, modify New Debt')
                    new_debt_budget_item.save()
        if not new_debt_category and cc_purchase_total:
            try:
                user = request.user
                expense_cat, cat_created = ExpenseCategory.objects.get_or_create(user=user, budget_period=bp, name='New Debt')
                expense_bi, created = ExpenseBudgetItem.objects.get_or_create(
                    user=user,
                    expense_category=expense_cat,
                    name='New Debt',
                    planned_amount=cc_purchase_total,
                )
                expense_bi.planned_amount = cc_purchase_total
                expense_bi.save()
            except IntegrityError:
                print(f'Your data has not been saved.')

        # Sum the planned expenses
        old_debt_paid = Decimal(0.00)

        expense_categories = bp.expense_categories.all()

        for category in expense_categories:
            for expense_budget_item in category.expense_budget_items.all():
                if expense_budget_item.name != 'New Debt':
                    total_planned_expenses += expense_budget_item.planned_amount

                # Check if reserved funds
                if expense_budget_item.type == 'Reserve':
                    total_actual_expenses += expense_budget_item.planned_amount
                    reserved_funds -= expense_budget_item.planned_amount

                for t in expense_budget_item.expense_transactions.all():
                    # total_actual_expenses += t.amount
                    all_transactions.append(t)
                    if t.credit_purchase:
                        total_new_debt += t.amount
                    else:
                        total_actual_expenses += t.amount
                    if t.credit_payoff:
                        old_debt_paid += t.amount
                        total_paid_debt += t.amount

        # Add debt payment transactions to all_transactions
        try:
            new_debt = bp.expense_categories.get(name='New Debt')
        except ExpenseCategory.DoesNotExist:
            new_debt = None
        if new_debt:
            # Remove New Debt from queryset and re-add it to a list to add it to the end
            expense_categories = expense_categories.exclude(name='New Debt')
            expense_categories = list(expense_categories)
            expense_categories.append(bp.expense_categories.get(name='New Debt'))

        sorted_transactions = sorted(all_transactions, key=lambda x: x.date, reverse=True)

    except BudgetPeriod.DoesNotExist:
        return HttpResponseRedirect('add-budget/')
    except Exception as err:
        return HttpResponseNotFound(f"Page not found! Here is the error: {err} {type(err)}")

    left_to_plan = total_planned_income - total_planned_expenses
    left_to_spend = total_actual_income - total_actual_expenses
    total_remaining_debt = total_new_debt - total_paid_debt

    debits_credits = total_actual_income - total_actual_expenses - reserved_funds
    current_balance = bp.starting_bank_balance + debits_credits

    return render(request,
                  'budgets/budget.html',
                  {
                   'month': month.capitalize(),
                   'year': year,
                   'income_budget_items': income_budget_items,
                   'expense_categories': expense_categories,
                   'new_debt': new_debt,
                   'total_planned_income': total_planned_income,
                   'total_planned_expenses': total_planned_expenses,
                   'total_actual_income': total_actual_income,
                   'total_actual_expenses': total_actual_expenses,
                   'total_new_debt': total_new_debt,
                   'total_paid_debt': total_paid_debt,
                   'total_remaining_debt': total_remaining_debt,
                   'left_to_plan': left_to_plan,
                   'left_to_spend': left_to_spend,
                   'bp_id': bp.id,
                   'all_transactions': sorted_transactions,
                   'starting_balance': bp.starting_bank_balance,
                   'debits_credits': debits_credits,
                   'current_balance': current_balance,
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
    fields = ['name', 'planned_amount', 'type']
    template_name = 'budgets/add_income_budget_item.html'
    success_url = './'
    success_message = 'Income budget item successfully added!'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        month, year = get_month_and_year_from_request(self.request)
        user = self.request.user
        context['budget_period'] = get_budget_period(user, month, year)
        return context

    def form_valid(self, form):
        month, year = get_month_and_year_from_request(self.request)
        user = self.request.user
        form.instance.budget_period = get_budget_period(user, month, year)
        form.instance.user = user
        return super(AddIncomeBudgetItem, self).form_valid(form)


class AddIncomeTransaction(SuccessMessageMixin, CreateView):
    model = IncomeTransaction
    fields = ['name', 'amount', 'date']
    template_name = 'budgets/add_income_transaction.html'
    success_message = 'Income transaction successfully added!'

    def get_success_url(self):
        if 'back_to_item_view' in self.request.POST:
            return './view'
        else:
            return '../../'

    def get_initial(self):
        return {
                'date': datetime.today(),
                }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['income_budget_item'] = IncomeBudgetItem.objects.get(id=self.request.get_full_path().split('/')[-2])
        except Exception as err:
            print('There was an error:', err)
            context['income_budget_item'] = None
        if self.request.META.get('HTTP_REFERER').split('/')[-1] == 'view':
            context['destination'] = 'back_to_item_view'
        else:
            context['destination'] = 'back_to_budget_view'
        return context

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.budget_item_id = self.request.get_full_path().split('/')[-2]
        return super(AddIncomeTransaction, self).form_valid(form)


class AddExpenseCategory(SuccessMessageMixin, CreateView):
    model = ExpenseCategory
    fields = ['name']
    template_name = 'budgets/add_expense_category.html'
    success_url = './'
    success_message = 'Expense category successfully added!'

    # def get_initial(self):
    #     bpid = None
    #     try:
    #         split_url = self.request.get_full_path().split('/')
    #         month = datetime.strptime(split_url[-3], '%B').month
    #         year = split_url[-2]
    #         bpid = BudgetPeriod.objects.get(user=self.request.user, month=month, year=year)
    #     except Exception as err:
    #         return HttpResponseNotFound(f"Page not found! Here is the error: {err} {type(err)}")
    #     return {'budget_period': bpid,}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        month, year = get_month_and_year_from_request(self.request)
        user = self.request.user
        context['budget_period'] = get_budget_period(user, month, year)
        return context

    def form_valid(self, form):
        month, year = get_month_and_year_from_request(self.request)
        user = self.request.user
        form.instance.budget_period = get_budget_period(user, month, year)
        form.instance.user = user
        return super(AddExpenseCategory, self).form_valid(form)


# TODO: Look this over, success url may need to be modified
class AddExpenseTransaction(SuccessMessageMixin, CreateView):
    template_name = 'budgets/add_expense_transaction.html'
    form_class = ExpenseTransactionForm
    success_url = '../../../../'
    success_message = 'Expense transaction successfully added!'

    def get_form_kwargs(self):
        kwargs = super(AddExpenseTransaction, self).get_form_kwargs()
        kwargs.update({'user': self.request.user.id})
        return kwargs

    def get_initial(self):
        # TODO: Make sure foreign key 'Budget Item' only shows that months items
        return {
                'date': datetime.today(),
                }

    def get_success_url(self):
        if 'back_to_item_view' in self.request.POST:
            return './view'
        else:
            return '../../../../'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['expense_budget_item'] = ExpenseBudgetItem.objects.get(id=self.request.get_full_path().split('/')[-2])
        except Exception as err:
            print('There was an error:', err)
            context['expense_budget_item'] = None
        if self.request.META.get('HTTP_REFERER').split('/')[-1] == 'view':
            context['destination'] = 'back_to_item_view'
        else:
            context['destination'] = 'back_to_budget_view'
        return context

    def form_valid(self, form):
        user = self.request.user
        form.instance.user = user
        form.instance.expense_budget_item_id = self.request.get_full_path().split('/')[-2]

        # If transaction was a credit purchase, add item to new debt expense
        if form.cleaned_data['credit_purchase']:
            month, year = get_month_and_year_from_request(self.request)
            bp = get_budget_period(user, month, year)
            expense_cat, cat_created = ExpenseCategory.objects.get_or_create(user=user, budget_period=bp, name='New Debt')

            try:
                expense_bi, created = ExpenseBudgetItem.objects.get_or_create(
                    user=user,
                    expense_category=expense_cat,
                    name='New Debt',
                    defaults={'planned_amount': 0},
                )
                expense_bi.planned_amount += form.cleaned_data['amount']
                expense_bi.save()
            except IntegrityError:
                return self.render_to_response(
                    self.get_context_data(
                        form=form,
                        message=f'Your data has not been saved because there is already an entry for {form.instance.date}.',
                    )
                )
        return super(AddExpenseTransaction, self).form_valid(form)


class AddExpenseBudgetItem(SuccessMessageMixin, CreateView):
    # TODO: Only show expense categories in that budget period
    model = ExpenseBudgetItem
    fields = ['name', 'planned_amount', 'type']
    template_name = 'budgets/add_expense_budget_item.html'
    success_url = '../../'
    success_message = 'Expense budget item successfully added!'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        expense_category_id = int(self.request.get_full_path().split('/')[-2])
        expense_category = ExpenseCategory.objects.get(id=expense_category_id)
        context['expense_category'] = expense_category
        return context

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.expense_category_id = self.request.get_full_path().split('/')[-2]
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
    datetime_object = datetime.strptime(month, '%B')
    month_by_num = datetime_object.month
    bp = BudgetPeriod.objects.get(month=month_by_num, year=year)

    context = {}
    try:
        context['income_budget_items'] = IncomeBudgetItem.objects.filter(budget_period=bp.id)
        context['expense_categories'] = ExpenseCategory.objects.filter(budget_period=bp.id)
    except IncomeBudgetItem.DoesNotExist or ExpenseCategory.DoesNotExist:
        return HttpResponseNotFound("Page not found!")
    context['month'] = month.capitalize()
    context['year'] = year

    return render(request, 'budgets/view_transactions.html', context)


class AddDebtPayment(SuccessMessageMixin, CreateView):
    template_name = 'budgets/add_debt_payment.html'
    form_class = ExpenseTransactionDebtPaymentForm
    success_url = '../'
    success_message = 'Debt payment successfully added!'

    def get_form_kwargs(self):
        kwargs = super(AddDebtPayment, self).get_form_kwargs()
        kwargs.update({'user': self.request.user.id})
        return kwargs

    def get_initial(self):
        return {
            'date': datetime.today(),
        }

    def form_valid(self, form):
        month, year = get_month_and_year_from_request(self.request)
        user = self.request.user.id
        bp = get_budget_period(user, month, year)
        new_debt_bi = bp.expense_categories.get(name='New Debt').expense_budget_items.get(name='New Debt').id

        self.object = form.save(commit=False)
        self.object.user_id = user
        self.object.expense_budget_item_id = new_debt_bi
        self.object.credit_payoff = True
        self.object.save()

        return super(AddDebtPayment, self).form_valid(form)


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

    totals['non_monthly_per_month_total'] = Decimal("{:.2f}".format(non_monthly_total / 12))

    context['totals'] = totals

    month_labels, year_month_tuple = get_last_12_months_labels(get_next_12=True)

    # Separate the month from the year on the last element in the list and add them to separate variables
    month_labels[11], year = month_labels[11].split(' ')

    # Loop through months and add the year next to Jan
    for idx, month in enumerate(month_labels):
        if month == 'Jan':
            month_labels[idx] = 'Jan ' + year

    item_data = []

    # Loop through a year of year/month pairs
    idx = 0
    for year, month in year_month_tuple:
        # Loop through all schedule items
        month_total = Decimal(0.0)
        for item in ScheduleItem.objects.filter(user=request.user.id).exclude(frequency="Monthly"):
            month_total += item.get_monthly_total(int(year), int(month))
        item_data.append((month_labels[idx], "{:0.2f}".format(month_total)))
        idx += 1

    context['month_data'] = item_data

    # TODO: Fix month column to show the new year next to January
    # TODO: Fix alignment and formatting
    return render(request, 'schedule/view_schedule.html', context)


class AddScheduleItem(SuccessMessageMixin, CreateView):
    model = ScheduleItem
    fields = ['name', 'amount', 'category', 'first_due_date', 'frequency']
    template_name = 'schedule/add_schedule_item.html'
    success_url = '/schedule/'
    success_message = 'Schedule item successfully added!'

    def form_valid(self, form):
        form.instance.user = self.request.user
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


# Report Views
# TODO: Asset and debts reports
# TODO: Money schedule reports
# TODO: Budget reports
def view_reports(request):
    return render(request, 'budgets/reports.html')


# Offers page
# TODO: Add offers page
# TODO: Offer Discover credit card
# TODO: Changing payment times to make sure you have money to pay bills between paychecks
# TODO: 1-month advance in your checking to give you cushion
# TODO: 3-6 months savings reserve
# TODO: Account balance is currently low
# TODO: Account balance will be too low to pay future expenses based on money cycle
# TODO: Upcoming expenses
def view_offers(request):
    return render(request, 'budgets/offers.html')


# Support Views
# TODO: Create support articles
# TODO: Create a support form
def view_support(request):
    return render(request, 'budgets/support.html')

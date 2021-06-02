from decimal import Decimal

from django.db import models
from django.db.models import Sum, Count
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

INCOME_OR_EXPENSE = (
    ('Income', 'Income'),
    ('Expense', 'Expense'),
)

FREQUENCY = (
    ('Weekly', 'Weekly'),
    ('Every two weeks', 'Every two weeks'),
    ('Monthly', 'Monthly'),
    ('Every two months', 'Every two months'),
    ('Quarterly', 'Quarterly'),
    ('Every six months', 'Every six months'),
    ('Yearly', 'Yearly'),
    ('One time only', 'One time only'),
)

MONTHS = (
    ('01', 'Jan'),
    ('02', 'Feb'),
    ('03', 'Mar'),
    ('04', 'Apr'),
    ('05', 'May'),
    ('06', 'Jun'),
    ('07', 'Jul'),
    ('08', 'Aug'),
    ('09', 'Sep'),
    ('10', 'Oct'),
    ('11', 'Nov'),
    ('12', 'Dec'),
)

NEED_WANT_SAVINGS_DEBT = (
    ('Need', 'Need'),
    ('Want', 'Want'),
    ('Savings & Debt', 'Savings & Debt'),
)


# Asset and Debt Models
class Asset(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, default=1)
    name = models.CharField(max_length=50)
    type = models.CharField(max_length=50, blank=True)

    def __str__(self):
        if self.type == '':
            return self.name
        else:
            return self.name + ' - ' + self.type

    class Meta:
        ordering = ('name',)
        unique_together = ('user', 'name',)


class Debt(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, default=1)
    name = models.CharField(max_length=50)
    type = models.CharField(max_length=50, blank=True, default='')
    interest_rate = models.DecimalField(max_digits=9, decimal_places=4, blank=True, null=True)

    def __str__(self):
        if self.type == '':
            return self.name
        else:
            return self.name + ' - ' + self.type

    class Meta:
        ordering = ('name',)
        unique_together = ('user', 'name',)
        abstract = True


class InstallmentDebt(Debt):
    initial_amount = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
    minimum_payment = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
    payoff_date = models.DateField(blank=True, null=True)


class RevolvingDebt(Debt):
    credit_limit = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)


class Balance(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, default=1)
    balance = models.DecimalField(max_digits=9, decimal_places=2)
    date = models.DateField(blank=True, null=True)

    def __str__(self):
        return str(self.balance)

    def __float__(self):
        if self.balance is None:
            return 0.00
        else:
            return float(self.balance)

    class Meta:
        get_latest_by = 'date'
        abstract = True


class AssetBalance(Balance):
    asset = models.ForeignKey('Asset', on_delete=models.CASCADE, related_name='balances')

    class Meta:
        unique_together = ('user', 'asset', 'date',)
        ordering = ('-date', 'asset')


class InstallmentDebtBalance(Balance):
    debt = models.ForeignKey('InstallmentDebt', on_delete=models.CASCADE, related_name='balances')

    class Meta:
        unique_together = ('user', 'debt', 'date',)
        ordering = ('-date', 'debt')


class RevolvingDebtBalance(Balance):
    debt = models.ForeignKey('RevolvingDebt', on_delete=models.CASCADE, related_name='balances')

    class Meta:
        unique_together = ('user', 'debt', 'date',)
        ordering = ('-date', 'debt')


# Budget Models
class BudgetPeriod(models.Model):
    CHOICES = (
        (1, 'Jan'),
        (2, 'Feb'),
        (3, 'Mar'),
        (4, 'Apr'),
        (5, 'May'),
        (6, 'Jun'),
        (7, 'Jul'),
        (8, 'Aug'),
        (9, 'Sep'),
        (10, 'Oct'),
        (11, 'Nov'),
        (12, 'Dec'),
    )
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, default=1)
    month = models.IntegerField(choices=CHOICES, default=datetime.today().month)
    year = models.PositiveIntegerField(default=datetime.today().year)
    starting_bank_balance = models.DecimalField(max_digits=9, decimal_places=2, null=True)

    class Meta:
        unique_together = ('user', 'month', 'year',)
        verbose_name_plural = 'Monthly budget info'

    def __str__(self):
        return str(self.year) + ' - ' + str(self.CHOICES[self.month-1][1])


class IncomeBudgetItem(models.Model):
    INCOME_CHOICES = (
        ('Income', 'Income'),
        ('Transfer', 'Transfer'),
        ('Reserve', 'Reserve'),
    )

    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, default=1)
    budget_period = models.ForeignKey('BudgetPeriod', on_delete=models.CASCADE, related_name='income_budget_items')
    name = models.CharField(max_length=50)
    planned_amount = models.DecimalField(max_digits=9, decimal_places=2)
    type = models.CharField(max_length=50, choices=INCOME_CHOICES, default='Income')

    def __str__(self):
        return self.name + ' - ' + str(self.budget_period)

    def get_total_transactions(self):
        return self.income_transactions.count()

    def get_total_received(self):
        return self.income_transactions.aggregate(Sum('amount'))['amount__sum'] or 0

    class Meta:
        ordering = ('-planned_amount', 'name',)
        unique_together = ('user', 'budget_period', 'name',)


class IncomeTransaction(models.Model):
    # TODO: Add limited_choices_to in budget_item to prevent seeing other months items
    # https://stackoverflow.com/questions/31578559/django-foreignkey-limit-choices-to-a-different-foreignkey-id
    # https://stackoverflow.com/questions/7133455/django-limit-choices-to-doesnt-work-on-manytomanyfield
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, default=1)
    budget_item = models.ForeignKey('IncomeBudgetItem',
                                    on_delete=models.CASCADE,
                                    related_name='income_transactions',
                                    # limit_choices_to={"budget_period_id": 2},
                                    )
    name = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    date = models.DateField()

    def get_signed_value(self):
        return f'+{self.amount}'

    def __float__(self):
        if self.amount is None:
            return 0.00
        else:
            return float(self.amount)

    def __str__(self):
        return self.name + ' for ' + '$' + str(self.amount) + ' on ' + str(self.date)

    class Meta:
        ordering = ('-amount', 'name',)
        # unique_together = ('user', 'budget_item', 'name',)



class ExpenseCategory(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, default=1)
    budget_period = models.ForeignKey('BudgetPeriod', on_delete=models.CASCADE, related_name='expense_categories')
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name + ' for ' + str(self.budget_period)

    class Meta:
        verbose_name_plural = 'Expense categories'
        unique_together = ('user', 'name', 'budget_period')

class ExpenseBudgetItem(models.Model):
    EXPENSE_CHOICES = (
        ('Expense', 'Expense'),
        ('Transfer', 'Transfer'),
        ('Reserve', 'Reserve'),
    )
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, default=1)
    expense_category = models.ForeignKey('ExpenseCategory', on_delete=models.CASCADE, related_name='expense_budget_items')
    name = models.CharField(max_length=50)
    planned_amount = models.DecimalField(max_digits=9, decimal_places=2)
    type = models.CharField(max_length=50, choices=EXPENSE_CHOICES, default='Expense')

    def __str__(self):
        return self.name + ' for $' + str(self.planned_amount) + ' : ' + str(self.expense_category)

    def __float__(self):
        if self.amount is None:
            return 0.00
        else:
            return float(self.amount)

    def get_total_transactions(self):
        return self.expense_transactions.count()

    def get_total_spent(self):
        return self.expense_transactions.aggregate(Sum('amount'))['amount__sum'] or 0

    class Meta:
        unique_together = ('user', 'name', 'expense_category')


class ExpenseTransaction(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, default=1)
    expense_budget_item = models.ForeignKey('ExpenseBudgetItem', on_delete=models.CASCADE, related_name='expense_transactions')
    name = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    credit_purchase = models.BooleanField(default=False)
    credit_payoff = models.BooleanField(default=False)
    date = models.DateField()

    def __str__(self):
        return f'{self.date} - {self.name}'

    def get_signed_value(self):
        return f'-{self.amount}'

class ScheduleItem(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, default=1)
    name = models.CharField(max_length=50)
    category = models.CharField(max_length=50, default="", blank=True)
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    first_due_date = models.DateField()
    # end_date = models.DateField()
    frequency = models.CharField(max_length=50, choices=FREQUENCY)

    def __str__(self):
        return f'{self.name} - {self.amount} - {self.first_due_date} - {self.frequency}'

    def get_time_delta(self):
        if self.frequency == 'Weekly':
            td = timedelta(weeks=1)
        elif self.frequency == 'Every two weeks':
            td = timedelta(weeks=2)
        elif self.frequency == 'Monthly':
            td = relativedelta(months=+1)
        elif self.frequency == 'Every two months':
            td = relativedelta(months=+2)
        elif self.frequency == 'Quarterly':
            td = relativedelta(months=+4)
        elif self.frequency == 'Every six months':
            td = relativedelta(months=+6)
        elif self.frequency == 'Yearly':
            td = relativedelta(years=+1)
        elif self.frequency == 'One time only':
            pass # TODO: Do I need to implement something here? I could run into issues in the future
        return td

    def get_next_payment(self):
        """Calculates the next payment date"""
        current_date = date.today()

        # If the first due date hasn't happened yet, that will be the next payment
        if self.first_due_date >= current_date:
            return self.first_due_date

        # Assign Time Delta Based On Frequency
        td = self.get_time_delta()

        date_to_check = self.first_due_date

        # Increment the date until it is past the current date and then return that date
        while current_date > date_to_check:
            date_to_check += td
        return date_to_check

    def get_budget_period_occurrences(self, month, year):
        """Will check the schedule item to see if it exists that month"""
        # TODO: add functionality to this method
        pass

    def get_monthly_total(self, year, month):
        """Returns the total amount due for a money schedule item in a particular year/month pair"""

        # Get the time delta to find due dates
        time_delta = self.get_time_delta()

        # Set the date cutoff - 1st day of the following month
        date_cutoff = date(year, month, 1) + relativedelta(months=+1)

        total_amount = Decimal(0.0)
        date_to_check = self.first_due_date

        # Check for recurring due dates
        while date_cutoff > date_to_check:
            if date_to_check.month == month and date_to_check.year == year:
                total_amount += self.amount
            date_to_check += time_delta

        # print(f'The total for {self.name} for the date ({year}, {month}) is ${total_amount}')
        return total_amount

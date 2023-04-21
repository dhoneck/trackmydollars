from datetime import datetime, date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.db import models
from django.db.models import Sum

# For schedule item objects
FREQUENCY_CHOICES = (
    ('Weekly', 'Weekly'),
    ('Every two weeks', 'Every two weeks'),
    ('Monthly', 'Monthly'),
    ('Every two months', 'Every two months'),
    ('Quarterly', 'Quarterly'),
    ('Every six months', 'Every six months'),
    ('Yearly', 'Yearly'),
    ('One time only', 'One time only'),
)

# For schedule item objects
INCOME_EXPENSE_CHOICES = (
    ('Income', 'Income'),
    ('Transfer', 'Income Transfer'),
    ('Reserve', 'Income Reserve'),
    ('Expense', 'Expense'),
    ('Transfer', 'Expense Transfer'),
    ('Reserve', 'Expense Reserve'),
)

# For budget period objects
MONTH_CHOICES = (
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

# For income budget item objects
INCOME_CHOICES = (
    ('Income', 'Income'),
    ('Transfer', 'Transfer'),
    ('Reserve', 'Reserve'),
)

# For expense budget item objects
EXPENSE_CHOICES = (
    ('Expense', 'Expense'),
    ('Transfer', 'Transfer'),
    ('Reserve', 'Reserve'),
)

# Asset and Debt Models
class Asset(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
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
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    type = models.CharField(max_length=50, blank=True)
    interest_rate = models.DecimalField(max_digits=11, decimal_places=4, blank=True, null=True)

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
    initial_amount = models.DecimalField(max_digits=11, decimal_places=2, blank=True, null=True)
    minimum_payment = models.DecimalField(max_digits=11, decimal_places=2, blank=True, null=True)
    payoff_date = models.DateField(blank=True, null=True)


class RevolvingDebt(Debt):
    credit_limit = models.DecimalField(max_digits=11, decimal_places=2, blank=True, null=True)


class Balance(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=11, decimal_places=2)
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


# Money Schedule Models
class ScheduleItem(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    category = models.CharField(max_length=50)
    type = models.CharField(max_length=50, choices=INCOME_EXPENSE_CHOICES, default='Expense')
    amount = models.DecimalField(max_digits=11, decimal_places=2)
    first_due_date = models.DateField()
    frequency = models.CharField(max_length=50, choices=FREQUENCY_CHOICES)

    def __str__(self):
        return f'{self.name} - {self.amount} - {self.first_due_date} - {self.frequency}'

    def get_time_delta(self):
        """
        Gets the time delta based on frequency.

        Returns:
            dateutil.relativedelta.relativedelta: The difference in time between due dates.
        """
        if self.frequency == 'Weekly':
            return relativedelta(weeks=+1)
        elif self.frequency == 'Every two weeks':
            return relativedelta(weeks=+2)
        elif self.frequency == 'Monthly':
            return relativedelta(months=+1)
        elif self.frequency == 'Every two months':
            return relativedelta(months=+2)
        elif self.frequency == 'Quarterly':
            return relativedelta(months=+4)
        elif self.frequency == 'Every six months':
            return relativedelta(months=+6)
        elif self.frequency == 'Yearly':
            return relativedelta(years=+1)
        elif self.frequency == 'One time only':
            return relativedelta(days=0)

    def get_next_payment(self):
        """
        Returns the next payment date or None if no next payment found.

        Returns:
            date | None: The next payment date or none if object is one time only and the due date has passed.
        """
        current_date = date.today()

        # If the first due date hasn't happened yet, that will be the next payment
        if self.first_due_date >= current_date:
            return self.first_due_date

        # If item is one time only and is already past due it will return None
        if self.frequency == 'One time only':
            return None

        # Assign time delta based on frequency
        time_delta = self.get_time_delta()
        date_to_check = self.first_due_date

        # Increment the date until it is past the current date and then return that date
        while current_date > date_to_check:
            date_to_check += time_delta
        return date_to_check

    def get_monthly_total(self, year, month):
        """
        Returns the total amount due for a money schedule item in a particular year/month pair.

        Parameters:
            year (int): The year of which you are tryin to get a total from.
            month (int): The month of which you are tryin to get a total from.
        Returns:
            Decimal: The total amount for this item in this year/month pair.
        """
        year = int(year)
        month = int(month)
        # Check if item is one time only
        if self.frequency == 'One time only':
            # Check if item is happening this month/year
            if self.first_due_date.month == month and self.first_due_date.year == year:
                return self.amount
            else:
                return Decimal(0.00)

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

        return total_amount

    def monthly_occurrences(self, year, month):
        """
        Returns the total amount due for a money schedule item in a particular year/month pair.

        Parameters:
            year (int): The year of which you are tryin to get a total from.
            month (int): The month of which you are tryin to get a total from. Jan is 1 and Dec is 12.

        Returns:
            list[ScheduleItem, Decimal] or None: A list containing object and total for the year/month pair or None.
        """
        # Check if item is one time only
        if self.frequency == 'One time only':
            # Check if item is happening this month/year
            if self.first_due_date.month == month and self.first_due_date.year == year: # Happening this month
                return [self, self.amount]
            else: # Not happening this month
                return None

        # Get the time delta to find due dates
        time_delta = self.get_time_delta()

        # Set the initial due date and date cutoff (1st day of the month)
        date_to_check = self.first_due_date
        date_cutoff = date(year, month, 1) + relativedelta(months=+1)

        # Check for recurring due dates for this month/year and total the payments
        occurrences = [self, Decimal(0.00)]
        while date_cutoff > date_to_check:
            if date_to_check.month == month and date_to_check.year == year:
                occurrences[1] += self.amount
            date_to_check += time_delta

        if occurrences[1]: # If balanced is not 0
            return occurrences
        else:
            return None

    def is_active(self):
        """
        Check if there is a future due date. All are true except one time only items that have past already.

        Returns:
            bool: A boolean that states whether there is a future due date.
        """
        if self.frequency != 'One time only':
            return True
        else:
            today = date.today();
            if self.first_due_date >= today:
                return True
            else:
                return False


# Budget Models
class BudgetPeriod(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    month = models.IntegerField(choices=MONTH_CHOICES, default=datetime.today().month)
    year = models.PositiveIntegerField(default=datetime.today().year)
    starting_bank_balance = models.DecimalField(max_digits=11, decimal_places=2, null=True, default=0.00)
    starting_cash_balance = models.DecimalField(max_digits=11, decimal_places=2, null=True, default=0.00)

    class Meta:
        unique_together = ('user', 'month', 'year',)
        verbose_name_plural = 'Monthly budget info'

    def __str__(self):
        return str(self.year) + ' - ' + str(MONTH_CHOICES[self.month - 1][1])


class IncomeBudgetItem(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    budget_period = models.ForeignKey('BudgetPeriod', on_delete=models.CASCADE, related_name='income_budget_items')
    name = models.CharField(max_length=50)
    planned_amount = models.DecimalField(max_digits=11, decimal_places=2)
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
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    budget_item = models.ForeignKey('IncomeBudgetItem',
                                    on_delete=models.CASCADE,
                                    related_name='income_transactions',
                                    )
    name = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=11, decimal_places=2)
    cash = models.BooleanField(default=False)
    date = models.DateField()

    def get_signed_value(self):
        return f'+{self.amount}'

    def is_positive(self):
        return True

    def __float__(self):
        if self.amount is None:
            return 0.00
        else:
            return float(self.amount)

    def __str__(self):
        return self.name + ' for ' + '$' + str(self.amount) + ' on ' + str(self.date)

    class Meta:
        ordering = ('-amount', 'name',)


class ExpenseCategory(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    budget_period = models.ForeignKey('BudgetPeriod', on_delete=models.CASCADE, related_name='expense_categories')
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name + ' for ' + str(self.budget_period)

    def is_new_debt(self):
        if self.name == 'New Debt':
            return True
        else:
            return False

    class Meta:
        verbose_name_plural = 'Expense categories'
        unique_together = ('user', 'name', 'budget_period')


class ExpenseBudgetItem(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    expense_category = models.ForeignKey('ExpenseCategory', on_delete=models.CASCADE, related_name='expense_budget_items')
    name = models.CharField(max_length=50)
    planned_amount = models.DecimalField(max_digits=11, decimal_places=2)
    type = models.CharField(max_length=50, choices=EXPENSE_CHOICES, default='Expense')

    def __str__(self):
        return self.name + ' - ' + str(self.expense_category)

    def __float__(self):
        if self.planned_amount is None:
            return 0.00
        else:
            return float(self.planned_amount)

    def get_total_transactions(self):
        return self.expense_transactions.count()

    def get_total_spent(self):
        return self.expense_transactions.aggregate(Sum('amount'))['amount__sum'] or 0

    class Meta:
        unique_together = ('user', 'name', 'expense_category')


class ExpenseTransaction(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    expense_budget_item = models.ForeignKey('ExpenseBudgetItem', on_delete=models.CASCADE, related_name='expense_transactions')
    name = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=11, decimal_places=2)
    credit_purchase = models.BooleanField(default=False)
    credit_payoff = models.BooleanField(default=False)
    cash = models.BooleanField(default=False)
    date = models.DateField()

    def __str__(self):
        return f'{self.date} - {self.name}'

    def get_signed_value(self):
        if self.amount < 0:  # For negative expenses (refunds)
            return f'+{abs(self.amount)}'
        else:
            return f'-{self.amount}'

    def is_positive(self):
        if self.amount < 0:
            return True
        else:
            return False

    def is_refund(self):
        return self.is_positive()


class ContactEntry(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    reason_for_contact = models.CharField(max_length=100)
    description = models.TextField()
    date_submitted = models.DateField(auto_now=True)

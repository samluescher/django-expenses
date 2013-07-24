from expenses.random_id import random_id
from expenses.templatetags.moneyformats import money
from time_tracking.middleware import CurrentUserMiddleware
from django.db import models
from django.utils.formats import get_format
from django.utils.translation import ugettext_lazy as _
from django.template.defaultfilters import date as format_date
from django.contrib.auth.models import User, Group, Permission
from django.db.models import Q
import datetime

BILL_NO_LENGTH = 6
DATE_FORMAT = get_format('DATE_FORMAT')


class ExpensesGroup(Group):

    def __init__(self, *args, **kwargs):
        super(ExpensesGroup, self).__init__(*args, **kwargs)
        #self._meta.get_field('permissions').editable = False

    class Meta:
        proxy = True
        verbose_name = _('Group')
        verbose_name_plural = _('Groups')
    
    #def save(self, *args, **kwargs):
    #    permission_codenames = ('add_expense', 'change_expense', 'delete_expense', 'add_expensetype', 'change_expensetype', 'delete_expensetype')
    #    permissions = Permission.objects.filter(content_type__app_label='expenses', codename__in=permission_codenames)
    #    for permission in permissions: 
    #        self.permissions.add(permission)
    #    self.name = 'asd'
        
    #    super(ExpensesGroup, self).save(*args, **kwargs)
       # raise Exception(self.permissions.all())

    @staticmethod
    def get_default():
        try:
            return CurrentUserMiddleware.get_current_user_groups()[0]
        except IndexError:
            return None

class ExpenseType(models.Model):
    name = models.CharField(_('name'), max_length=255)
    default = models.BooleanField(_('default'), max_length=255)
    
    class Meta:
        verbose_name = _('expense type')
        verbose_name_plural = _('expense types')
        ordering = ['-default', 'name']
    
    def __unicode__(self):
        return self.name
    
    @staticmethod
    def get_default():
        try:
            return ExpenseType.objects.all()[0]
        except (IndexError, ExpenseType.DoesNotExist):
            return None


class Bill(models.Model):
    CREATED = 100
    CLOSED = 900
    STATUS_CHOICES = (
        (CREATED, _('created')),
        (CLOSED, _('closed')),
    )
    bill_no = models.CharField(_('reference #'), editable=False, max_length=BILL_NO_LENGTH)
    created = models.DateField(_('date'), auto_now_add=True)
    modified = models.DateField(_('date'), auto_now=True)
    status = models.IntegerField(_('status'), choices=STATUS_CHOICES, default=CREATED)

    class Meta:
        verbose_name = _('bill')
        verbose_name_plural = _('bills')
        ordering = ['-created']

    def __unicode__(self):
        return '#%(bill_no)s (%(date)s)' % {'bill_no': self.bill_no, 'date': format_date(self.created, DATE_FORMAT)}

    def save(self, *args, **kwargs):
        if not self.bill_no:
            self.bill_no = random_id(BILL_NO_LENGTH).upper()
        return super(Bill, self).save()


class Expense(models.Model):
    date = models.DateField(_('date'), default=datetime.datetime.today)
    user = models.ForeignKey(User, verbose_name=_('user'), default=CurrentUserMiddleware.get_current_user, editable=False)
    bill = models.ForeignKey(Bill, verbose_name=_('bill'), editable=False, null=True, blank=True)
    amount = models.DecimalField(_('amount'), max_digits=10, decimal_places=2)
    expense_type = models.ForeignKey(ExpenseType, verbose_name=_('type'), null=False, blank=False, default=ExpenseType.get_default)
    expense_group = models.ForeignKey(ExpensesGroup, verbose_name=_('group'), null=False, blank=False, default=ExpensesGroup.get_default, limit_choices_to={'pk__in': CurrentUserMiddleware.get_current_user_groups})
    comment = models.TextField(_('comment'), blank=True, default='')
    billed = models.BooleanField(_('billed'), editable=False)
    created = models.DateField(_('date'), auto_now_add=True)
    modified = models.DateField(_('date'), auto_now=True)

    class Meta:
        verbose_name = _('expense')
        verbose_name_plural = _('expenses')
        ordering = ['-date', 'user', 'expense_type']

    def __unicode__(self):
        return _('%(date)s: %(amount)s (%(user)s)') % {
            'date': format_date(self.date, DATE_FORMAT),
            'user': self.user.__unicode__(),
            'amount': money(self.amount)
        }

    @staticmethod
    def summarize(user, qs, bill=None):
        if bill:
            expenses = qs.filter(bill=bill)
        else:
            expenses = qs
        summary = expenses.aggregate(expenses_total=models.Sum('amount'), 
            from_date=models.Min('date'), to_date=models.Max('date'))
        expenses_total = summary['expenses_total']
        from_date = summary['from_date']
        to_date = summary['to_date']
        if from_date and to_date:
            days = (to_date - from_date).days + 1
        else:
            days = 0

        involved_types = ExpenseType.objects.filter(pk__in=expenses.values('expense_type'))
        involved_groups = ExpensesGroup.objects.filter(pk__in=expenses.values('expense_group'))
        involved_users = []
        for expense_group in involved_groups:
            for user in expense_group.user_set.all():
                if not user in involved_users:
                    involved_users.append(user)
        expenses_by_user = expenses.values('user').annotate(total=models.Sum('amount'), count=models.Count('pk'))
        expenses_per_user = expenses_total / len(involved_users) if len(involved_users) else 0
        expenses_by_involved_user = []
        for user in involved_users:
            add_item = {'total': 0, 'count': 0}
            for item in expenses_by_user:
                if item['user'] == user.pk:
                    add_item = item 
                    break
            add_item['user'] = user
            add_item['balance'] = add_item['total'] - expenses_per_user
            expenses_by_involved_user.append(add_item)

        return {
            'bill': bill,
            'expenses': {
                'count': expenses.count(),
                'total': expenses_total,
                'by_user': expenses_by_involved_user,
                'average_daily': expenses_total / days if days != 0 else 0, 
                'average_user': expenses_per_user, 
            },
            'groups': involved_groups,
            'types': involved_types,
            'dates': {
                'days': days,
                'from': from_date,
                'to': to_date,
            }
        }

        return {}
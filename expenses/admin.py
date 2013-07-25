from expenses.models import Expense, ExpenseType, ExpensesGroup, Bill
from expenses.templatetags.moneyformats import money
from django.contrib.admin.views.main import ChangeList
from django.contrib import admin
from django.contrib.admin.util import unquote
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _, ugettext
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.db.models import Sum
import datetime


def reset_bill(modeladmin, request, queryset):
    queryset.update(bill=None, billed=False)
reset_bill.short_description = _('Reset bill for selected entries')


class ExpenseAdmin(admin.ModelAdmin):
    date_hierarchy = 'date'
    list_display = ('date', 'user', 'amount', 'expense_type', 'expense_group', 'comment', 'bill')
    list_filter = ('billed', 'date', 'user', 'expense_type', 'expense_group', 'bill')
    
    actions = [reset_bill]

    def get_actions(self, request):
        actions = super(ExpenseAdmin, self).get_actions(request)
        if not request.user.is_superuser:
            del actions['reset_bill']
        return actions
    
    def save_model(self, request, obj, form, change):
        if not obj.user:
            obj.user = request.user
        return super(ExpenseAdmin, self).save_model(request, obj, form, change)

    def queryset(self, request):
        """
        Filter the objects displayed in the change_list to only
        display those for the currently signed in user.
        """
        qs = super(ExpenseAdmin, self).queryset(request)
        if not request.user.is_superuser:
            qs = qs.filter(expense_group__in=request.user.groups.all())
        return qs

    def get_changelist_queryset(self, request):
        cl = ChangeList(request, self.model, self.list_display, self.list_display_links,
            self.list_filter, self.date_hierarchy, self.search_fields,
            self.list_select_related, self.list_per_page, self.list_max_show_all, self.list_editable, self)
        return cl.get_query_set(request)

    def changelist_view(self, request, extra_context=None):
        qs = self.get_changelist_queryset(request)
        bill_id = request.GET.get('bill__id__exact', False)
        bill = None
        if bill_id:
            try:
                bill = Bill.objects.get(pk=bill_id)
            except Bill.DoesNotExist:
                pass
        bill_confirm = request.POST.get('confirm', False)
        if qs.filter(billed=False).count() > 0 and not bill:
            if bill_confirm:
                qs = qs.filter(billed=False)
                bill_url = reverse('admin:expense_bill')+'?'+request.META['QUERY_STRING']
            else:
                bill_url = reverse('admin:expenses_expense_changelist')+'?'+request.META['QUERY_STRING']+'&billed__exact=0'
        else:
            confirm_bill = bill_url = False
            
        extra_context = {
            'expense_info': Expense.summarize(request.user, qs, bill),
            'bill_url': bill_url,
            'bill_confirm': bill_confirm,
        }
        
        return super(ExpenseAdmin, self).changelist_view(request, extra_context)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or (obj and obj.user == request.user)

    def has_change_permission(self, request, obj=None):
        return not obj or request.user.is_superuser or (obj and obj.user == request.user)

    def change_view(self, request, object_id, *args, **kwargs):
        obj = self.get_object(request, unquote(object_id))
        if not self.has_change_permission(request, obj):
            messages.info(request, _('You can only change your own entries.'))
            return HttpResponseRedirect(reverse('admin:expenses_expense_changelist'))
        else:
            return super(ExpenseAdmin, self).change_view(request, object_id, *args, **kwargs)

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url
        urls = super(ExpenseAdmin, self).get_urls()
        url_patterns = patterns('',
            url(r'^bill/$', self.admin_site.admin_view(self.bill), name="expense_bill"),
        )
        url_patterns.extend(urls)
        return url_patterns
        
    def bill(self, request):
        qs = self.get_changelist_queryset(request).filter(billed=False)
        if qs.count() > 0:
            bill = Bill()
            bill.save()
            for item in qs.filter(bill=None):
                item.bill = bill
                item.billed = True
                item.save()
                messages.add_message(request, messages.INFO, _('Bill %s was saved.') % bill)
        return HttpResponseRedirect(reverse('admin:expenses_expense_changelist')+'?'+request.META['QUERY_STRING'])


class ExpenseTypeAdmin(admin.ModelAdmin):
    pass


class ExpensesGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'user_names', 'expenses_sum')
    
    def user_names(self, obj):
        return ', '.join([user.__unicode__() for user in obj.user_set.all()])
    user_names.short_description = _('users')
    
    def expenses_sum(self, obj):
        return money(Expense.objects.filter(expense_group=obj).aggregate(Sum('amount'))['amount__sum'])
    expenses_sum.short_description = _('total')


class BillAdmin(admin.ModelAdmin):
    pass

admin.site.register(Expense, ExpenseAdmin)
admin.site.register(ExpenseType, ExpenseTypeAdmin)
admin.site.register(ExpensesGroup, ExpensesGroupAdmin)
admin.site.register(Bill, BillAdmin)

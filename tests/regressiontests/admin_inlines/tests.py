from __future__ import absolute_import

from django.contrib.admin.tests import AdminSeleniumWebDriverTestCase
from django.contrib.admin.helpers import InlineAdminForm
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

# local test models
from .admin import InnerInline
from .models import (Holder, Inner, Holder2, Inner2, Holder3, Inner3, Person,
    OutfitItem, Fashionista, Teacher, Parent, Child, Author, Book, Profile,
    ProfileCollection)


class TestInline(TestCase):
    urls = "regressiontests.admin_inlines.urls"
    fixtures = ['admin-views-users.xml']

    def setUp(self):
        holder = Holder(dummy=13)
        holder.save()
        Inner(dummy=42, holder=holder).save()
        self.change_url = '/admin/admin_inlines/holder/%i/' % holder.id

        result = self.client.login(username='super', password='secret')
        self.assertEqual(result, True)

    def tearDown(self):
        self.client.logout()

    def test_can_delete(self):
        """
        can_delete should be passed to inlineformset factory.
        """
        response = self.client.get(self.change_url)
        inner_formset = response.context['inline_admin_formsets'][0].formset
        expected = InnerInline.can_delete
        actual = inner_formset.can_delete
        self.assertEqual(expected, actual, 'can_delete must be equal')

    def test_readonly_stacked_inline_label(self):
        """Bug #13174."""
        holder = Holder.objects.create(dummy=42)
        inner = Inner.objects.create(holder=holder, dummy=42, readonly='')
        response = self.client.get('/admin/admin_inlines/holder/%i/'
                                   % holder.id)
        self.assertContains(response, '<label>Inner readonly label:</label>')

    def test_many_to_many_inlines(self):
        "Autogenerated many-to-many inlines are displayed correctly (#13407)"
        response = self.client.get('/admin/admin_inlines/author/add/')
        # The heading for the m2m inline block uses the right text
        self.assertContains(response, '<h2>Author-book relationships</h2>')
        # The "add another" label is correct
        self.assertContains(response, 'Add another Author-Book Relationship')
        # The '+' is dropped from the autogenerated form prefix (Author_books+)
        self.assertContains(response, 'id="id_Author_books-TOTAL_FORMS"')

    def test_inline_primary(self):
        person = Person.objects.create(firstname='Imelda')
        item = OutfitItem.objects.create(name='Shoes')
        # Imelda likes shoes, but can't cary her own bags.
        data = {
            'shoppingweakness_set-TOTAL_FORMS': 1,
            'shoppingweakness_set-INITIAL_FORMS': 0,
            'shoppingweakness_set-MAX_NUM_FORMS': 0,
            '_save': u'Save',
            'person': person.id,
            'max_weight': 0,
            'shoppingweakness_set-0-item': item.id,
        }
        response = self.client.post('/admin/admin_inlines/fashionista/add/', data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(Fashionista.objects.filter(person__firstname='Imelda')), 1)

    def test_tabular_non_field_errors(self):
        """
        Ensure that non_field_errors are displayed correctly, including the
        right value for colspan. Refs #13510.
        """
        data = {
            'title_set-TOTAL_FORMS': 1,
            'title_set-INITIAL_FORMS': 0,
            'title_set-MAX_NUM_FORMS': 0,
            '_save': u'Save',
            'title_set-0-title1': 'a title',
            'title_set-0-title2': 'a different title',
        }
        response = self.client.post('/admin/admin_inlines/titlecollection/add/', data)
        # Here colspan is "4": two fields (title1 and title2), one hidden field and the delete checkbock.
        self.assertContains(response, '<tr><td colspan="4"><ul class="errorlist"><li>The two titles must be the same</li></ul></td></tr>')

    def test_no_parent_callable_lookup(self):
        """Admin inline `readonly_field` shouldn't invoke parent ModelAdmin callable"""
        # Identically named callable isn't present in the parent ModelAdmin,
        # rendering of the add view shouldn't explode
        response = self.client.get('/admin/admin_inlines/novel/add/')
        self.assertEqual(response.status_code, 200)
        # View should have the child inlines section
        self.assertContains(response, '<div class="inline-group" id="chapter_set-group">')

    def test_callable_lookup(self):
        """Admin inline should invoke local callable when its name is listed in readonly_fields"""
        response = self.client.get('/admin/admin_inlines/poll/add/')
        self.assertEqual(response.status_code, 200)
        # Add parent object view should have the child inlines section
        self.assertContains(response, '<div class="inline-group" id="question_set-group">')
        # The right callabe should be used for the inline readonly_fields
        # column cells
        self.assertContains(response, '<p>Callable in QuestionInline</p>')

    def test_help_text(self):
        """
        Ensure that the inlines' model field help texts are displayed when
        using both the stacked and tabular layouts.
        Ref #8190.
        """
        response = self.client.get('/admin/admin_inlines/holder4/add/')
        self.assertContains(response, '<p class="help">Awesome stacked help text is awesome.</p>', 4)
        self.assertContains(response, '<img src="/static/admin/img/icon-unknown.gif" class="help help-tooltip" width="10" height="10" alt="(Awesome tabular help text is awesome.)" title="Awesome tabular help text is awesome." />', 1)

    def test_non_related_name_inline(self):
        """
        Ensure that multiple inlines with related_name='+' have correct form
        prefixes. Bug #16838.
        """
        response = self.client.get('/admin/admin_inlines/capofamiglia/add/')

        self.assertContains(response,
                '<input type="hidden" name="-1-0-id" id="id_-1-0-id" />', html=True)
        self.assertContains(response,
                '<input type="hidden" name="-1-0-capo_famiglia" id="id_-1-0-capo_famiglia" />', html=True)
        self.assertContains(response,
                '<input id="id_-1-0-name" type="text" class="vTextField" '
                'name="-1-0-name" maxlength="100" />', html=True)

        self.assertContains(response,
                '<input type="hidden" name="-2-0-id" id="id_-2-0-id" />', html=True)
        self.assertContains(response,
                '<input type="hidden" name="-2-0-capo_famiglia" id="id_-2-0-capo_famiglia" />', html=True)
        self.assertContains(response,
                '<input id="id_-2-0-name" type="text" class="vTextField" '
                'name="-2-0-name" maxlength="100" />', html=True)

class TestInlineMedia(TestCase):
    urls = "regressiontests.admin_inlines.urls"
    fixtures = ['admin-views-users.xml']

    def setUp(self):

        result = self.client.login(username='super', password='secret')
        self.assertEqual(result, True)

    def tearDown(self):
        self.client.logout()

    def test_inline_media_only_base(self):
        holder = Holder(dummy=13)
        holder.save()
        Inner(dummy=42, holder=holder).save()
        change_url = '/admin/admin_inlines/holder/%i/' % holder.id
        response = self.client.get(change_url)
        self.assertContains(response, 'my_awesome_admin_scripts.js')

    def test_inline_media_only_inline(self):
        holder = Holder3(dummy=13)
        holder.save()
        Inner3(dummy=42, holder=holder).save()
        change_url = '/admin/admin_inlines/holder3/%i/' % holder.id
        response = self.client.get(change_url)
        self.assertContains(response, 'my_awesome_inline_scripts.js')

    def test_all_inline_media(self):
        holder = Holder2(dummy=13)
        holder.save()
        Inner2(dummy=42, holder=holder).save()
        change_url = '/admin/admin_inlines/holder2/%i/' % holder.id
        response = self.client.get(change_url)
        self.assertContains(response, 'my_awesome_admin_scripts.js')
        self.assertContains(response, 'my_awesome_inline_scripts.js')

class TestInlineAdminForm(TestCase):
    urls = "regressiontests.admin_inlines.urls"

    def test_immutable_content_type(self):
        """Regression for #9362
        The problem depends only on InlineAdminForm and its "original"
        argument, so we can safely set the other arguments to None/{}. We just
        need to check that the content_type argument of Child isn't altered by
        the internals of the inline form."""

        sally = Teacher.objects.create(name='Sally')
        john = Parent.objects.create(name='John')
        joe = Child.objects.create(name='Joe', teacher=sally, parent=john)

        iaf = InlineAdminForm(None, None, {}, {}, joe)
        parent_ct = ContentType.objects.get_for_model(Parent)
        self.assertEqual(iaf.original.content_type, parent_ct)

class TestInlinePermissions(TestCase):
    """
    Make sure the admin respects permissions for objects that are edited
    inline. Refs #8060.

    """
    urls = "regressiontests.admin_inlines.urls"

    def setUp(self):
        self.user = User(username='admin')
        self.user.is_staff = True
        self.user.is_active = True
        self.user.set_password('secret')
        self.user.save()

        self.author_ct = ContentType.objects.get_for_model(Author)
        self.holder_ct = ContentType.objects.get_for_model(Holder2)
        self.book_ct = ContentType.objects.get_for_model(Book)
        self.inner_ct = ContentType.objects.get_for_model(Inner2)

        # User always has permissions to add and change Authors, and Holders,
        # the main (parent) models of the inlines. Permissions on the inlines
        # vary per test.
        permission = Permission.objects.get(codename='add_author', content_type=self.author_ct)
        self.user.user_permissions.add(permission)
        permission = Permission.objects.get(codename='change_author', content_type=self.author_ct)
        self.user.user_permissions.add(permission)
        permission = Permission.objects.get(codename='add_holder2', content_type=self.holder_ct)
        self.user.user_permissions.add(permission)
        permission = Permission.objects.get(codename='change_holder2', content_type=self.holder_ct)
        self.user.user_permissions.add(permission)

        author = Author.objects.create(pk=1, name=u'The Author')
        book = author.books.create(name=u'The inline Book')
        self.author_change_url = '/admin/admin_inlines/author/%i/' % author.id
        # Get the ID of the automatically created intermediate model for thw Author-Book m2m
        author_book_auto_m2m_intermediate = Author.books.through.objects.get(author=author, book=book)
        self.author_book_auto_m2m_intermediate_id = author_book_auto_m2m_intermediate.pk

        holder = Holder2.objects.create(dummy=13)
        inner2 = Inner2.objects.create(dummy=42, holder=holder)
        self.holder_change_url = '/admin/admin_inlines/holder2/%i/' % holder.id
        self.inner2_id = inner2.id

        self.assertEqual(
            self.client.login(username='admin', password='secret'),
            True)

    def tearDown(self):
        self.client.logout()

    def test_inline_add_m2m_noperm(self):
        response = self.client.get('/admin/admin_inlines/author/add/')
        # No change permission on books, so no inline
        self.assertNotContains(response, '<h2>Author-book relationships</h2>')
        self.assertNotContains(response, 'Add another Author-Book Relationship')
        self.assertNotContains(response, 'id="id_Author_books-TOTAL_FORMS"')

    def test_inline_add_fk_noperm(self):
        response = self.client.get('/admin/admin_inlines/holder2/add/')
        # No permissions on Inner2s, so no inline
        self.assertNotContains(response, '<h2>Inner2s</h2>')
        self.assertNotContains(response, 'Add another Inner2')
        self.assertNotContains(response, 'id="id_inner2_set-TOTAL_FORMS"')

    def test_inline_change_m2m_noperm(self):
        response = self.client.get(self.author_change_url)
        # No change permission on books, so no inline
        self.assertNotContains(response, '<h2>Author-book relationships</h2>')
        self.assertNotContains(response, 'Add another Author-Book Relationship')
        self.assertNotContains(response, 'id="id_Author_books-TOTAL_FORMS"')

    def test_inline_change_fk_noperm(self):
        response = self.client.get(self.holder_change_url)
        # No permissions on Inner2s, so no inline
        self.assertNotContains(response, '<h2>Inner2s</h2>')
        self.assertNotContains(response, 'Add another Inner2')
        self.assertNotContains(response, 'id="id_inner2_set-TOTAL_FORMS"')

    def test_inline_add_m2m_add_perm(self):
        permission = Permission.objects.get(codename='add_book', content_type=self.book_ct)
        self.user.user_permissions.add(permission)
        response = self.client.get('/admin/admin_inlines/author/add/')
        # No change permission on Books, so no inline
        self.assertNotContains(response, '<h2>Author-book relationships</h2>')
        self.assertNotContains(response, 'Add another Author-Book Relationship')
        self.assertNotContains(response, 'id="id_Author_books-TOTAL_FORMS"')

    def test_inline_add_fk_add_perm(self):
        permission = Permission.objects.get(codename='add_inner2', content_type=self.inner_ct)
        self.user.user_permissions.add(permission)
        response = self.client.get('/admin/admin_inlines/holder2/add/')
        # Add permission on inner2s, so we get the inline
        self.assertContains(response, '<h2>Inner2s</h2>')
        self.assertContains(response, 'Add another Inner2')
        self.assertContains(response, '<input type="hidden" id="id_inner2_set-TOTAL_FORMS" '
                            'value="3" name="inner2_set-TOTAL_FORMS" />', html=True)

    def test_inline_change_m2m_add_perm(self):
        permission = Permission.objects.get(codename='add_book', content_type=self.book_ct)
        self.user.user_permissions.add(permission)
        response = self.client.get(self.author_change_url)
        # No change permission on books, so no inline
        self.assertNotContains(response, '<h2>Author-book relationships</h2>')
        self.assertNotContains(response, 'Add another Author-Book Relationship')
        self.assertNotContains(response, 'id="id_Author_books-TOTAL_FORMS"')
        self.assertNotContains(response, 'id="id_Author_books-0-DELETE"')

    def test_inline_change_m2m_change_perm(self):
        permission = Permission.objects.get(codename='change_book', content_type=self.book_ct)
        self.user.user_permissions.add(permission)
        response = self.client.get(self.author_change_url)
        # We have change perm on books, so we can add/change/delete inlines
        self.assertContains(response, '<h2>Author-book relationships</h2>')
        self.assertContains(response, 'Add another Author-Book Relationship')
        self.assertContains(response, '<input type="hidden" id="id_Author_books-TOTAL_FORMS" '
                            'value="4" name="Author_books-TOTAL_FORMS" />', html=True)
        self.assertContains(response, '<input type="hidden" id="id_Author_books-0-id" '
                            'value="%i" name="Author_books-0-id" />' % self.author_book_auto_m2m_intermediate_id, html=True)
        self.assertContains(response, 'id="id_Author_books-0-DELETE"')

    def test_inline_change_fk_add_perm(self):
        permission = Permission.objects.get(codename='add_inner2', content_type=self.inner_ct)
        self.user.user_permissions.add(permission)
        response = self.client.get(self.holder_change_url)
        # Add permission on inner2s, so we can add but not modify existing
        self.assertContains(response, '<h2>Inner2s</h2>')
        self.assertContains(response, 'Add another Inner2')
        # 3 extra forms only, not the existing instance form
        self.assertContains(response, '<input type="hidden" id="id_inner2_set-TOTAL_FORMS" '
                                'value="3" name="inner2_set-TOTAL_FORMS" />', html=True)
        self.assertNotContains(response, '<input type="hidden" id="id_inner2_set-0-id" '
                            'value="%i" name="inner2_set-0-id" />' % self.inner2_id, html=True)

    def test_inline_change_fk_change_perm(self):
        permission = Permission.objects.get(codename='change_inner2', content_type=self.inner_ct)
        self.user.user_permissions.add(permission)
        response = self.client.get(self.holder_change_url)
        # Change permission on inner2s, so we can change existing but not add new
        self.assertContains(response, '<h2>Inner2s</h2>')
        # Just the one form for existing instances
        self.assertContains(response, '<input type="hidden" id="id_inner2_set-TOTAL_FORMS" '
                                'value="1" name="inner2_set-TOTAL_FORMS" />', html=True)
        self.assertContains(response, '<input type="hidden" id="id_inner2_set-0-id" '
                            'value="%i" name="inner2_set-0-id" />' % self.inner2_id, html=True)
        # max-num 0 means we can't add new ones
        self.assertContains(response, '<input type="hidden" id="id_inner2_set-MAX_NUM_FORMS" '
                                'value="0" name="inner2_set-MAX_NUM_FORMS" />', html=True)

    def test_inline_change_fk_add_change_perm(self):
        permission = Permission.objects.get(codename='add_inner2', content_type=self.inner_ct)
        self.user.user_permissions.add(permission)
        permission = Permission.objects.get(codename='change_inner2', content_type=self.inner_ct)
        self.user.user_permissions.add(permission)
        response = self.client.get(self.holder_change_url)
        # Add/change perm, so we can add new and change existing
        self.assertContains(response, '<h2>Inner2s</h2>')
        # One form for existing instance and three extra for new
        self.assertContains(response, '<input type="hidden" id="id_inner2_set-TOTAL_FORMS" '
                                'value="4" name="inner2_set-TOTAL_FORMS" />', html=True)
        self.assertContains(response, '<input type="hidden" id="id_inner2_set-0-id" '
                            'value="%i" name="inner2_set-0-id" />' % self.inner2_id, html=True)

    def test_inline_change_fk_change_del_perm(self):
        permission = Permission.objects.get(codename='change_inner2', content_type=self.inner_ct)
        self.user.user_permissions.add(permission)
        permission = Permission.objects.get(codename='delete_inner2', content_type=self.inner_ct)
        self.user.user_permissions.add(permission)
        response = self.client.get(self.holder_change_url)
        # Change/delete perm on inner2s, so we can change/delete existing
        self.assertContains(response, '<h2>Inner2s</h2>')
        # One form for existing instance only, no new
        self.assertContains(response, '<input type="hidden" id="id_inner2_set-TOTAL_FORMS" '
                                'value="1" name="inner2_set-TOTAL_FORMS" />', html=True)
        self.assertContains(response, '<input type="hidden" id="id_inner2_set-0-id" '
                            'value="%i" name="inner2_set-0-id" />' % self.inner2_id, html=True)
        self.assertContains(response, 'id="id_inner2_set-0-DELETE"')


    def test_inline_change_fk_all_perms(self):
        permission = Permission.objects.get(codename='add_inner2', content_type=self.inner_ct)
        self.user.user_permissions.add(permission)
        permission = Permission.objects.get(codename='change_inner2', content_type=self.inner_ct)
        self.user.user_permissions.add(permission)
        permission = Permission.objects.get(codename='delete_inner2', content_type=self.inner_ct)
        self.user.user_permissions.add(permission)
        response = self.client.get(self.holder_change_url)
        # All perms on inner2s, so we can add/change/delete
        self.assertContains(response, '<h2>Inner2s</h2>')
        # One form for existing instance only, three for new
        self.assertContains(response, '<input type="hidden" id="id_inner2_set-TOTAL_FORMS" '
                                'value="4" name="inner2_set-TOTAL_FORMS" />', html=True)
        self.assertContains(response, '<input type="hidden" id="id_inner2_set-0-id" '
                            'value="%i" name="inner2_set-0-id" />' % self.inner2_id, html=True)
        self.assertContains(response, 'id="id_inner2_set-0-DELETE"')


class SeleniumFirefoxTests(AdminSeleniumWebDriverTestCase):
    webdriver_class = 'selenium.webdriver.firefox.webdriver.WebDriver'
    fixtures = ['admin-views-users.xml']
    urls = "regressiontests.admin_inlines.urls"

    def test_add_inlines(self):
        """
        Ensure that the "Add another XXX" link correctly adds items to the
        inline form.
        """
        from selenium.common.exceptions import TimeoutException
        self.admin_login(username='super', password='secret')
        self.selenium.get('%s%s' % (self.live_server_url,
            '/admin/admin_inlines/profilecollection/add/'))

        # Check that there's only one inline to start with and that it has the
        # correct ID.
        self.failUnlessEqual(len(self.selenium.find_elements_by_css_selector(
            '.dynamic-profile_set')), 1)
        self.failUnlessEqual(self.selenium.find_elements_by_css_selector(
            '.dynamic-profile_set')[0].get_attribute('id'),
            'profile_set-0')
        self.failUnlessEqual(len(self.selenium.find_elements_by_css_selector(
            '.dynamic-profile_set#profile_set-0 input[name=profile_set-0-first_name]')), 1)
        self.failUnlessEqual(len(self.selenium.find_elements_by_css_selector(
            '.dynamic-profile_set#profile_set-0 input[name=profile_set-0-last_name]')), 1)

        # Add an inline
        self.selenium.find_element_by_link_text('Add another Profile').click()

        # Check that the inline has been added, that it has the right id, and
        # that it contains the right fields.
        self.failUnlessEqual(len(self.selenium.find_elements_by_css_selector(
            '.dynamic-profile_set')), 2)
        self.failUnlessEqual(self.selenium.find_elements_by_css_selector(
            '.dynamic-profile_set')[1].get_attribute('id'), 'profile_set-1')
        self.failUnlessEqual(len(self.selenium.find_elements_by_css_selector(
            '.dynamic-profile_set#profile_set-1 input[name=profile_set-1-first_name]')), 1)
        self.failUnlessEqual(len(self.selenium.find_elements_by_css_selector(
            '.dynamic-profile_set#profile_set-1 input[name=profile_set-1-last_name]')), 1)

        # Let's add another one to be sure
        self.selenium.find_element_by_link_text('Add another Profile').click()
        self.failUnlessEqual(len(self.selenium.find_elements_by_css_selector(
            '.dynamic-profile_set')), 3)
        self.failUnlessEqual(self.selenium.find_elements_by_css_selector(
            '.dynamic-profile_set')[2].get_attribute('id'), 'profile_set-2')
        self.failUnlessEqual(len(self.selenium.find_elements_by_css_selector(
            '.dynamic-profile_set#profile_set-2 input[name=profile_set-2-first_name]')), 1)
        self.failUnlessEqual(len(self.selenium.find_elements_by_css_selector(
            '.dynamic-profile_set#profile_set-2 input[name=profile_set-2-last_name]')), 1)

        # Enter some data and click 'Save'
        self.selenium.find_element_by_name('profile_set-0-first_name').send_keys('0 first name 1')
        self.selenium.find_element_by_name('profile_set-0-last_name').send_keys('0 last name 2')
        self.selenium.find_element_by_name('profile_set-1-first_name').send_keys('1 first name 1')
        self.selenium.find_element_by_name('profile_set-1-last_name').send_keys('1 last name 2')
        self.selenium.find_element_by_name('profile_set-2-first_name').send_keys('2 first name 1')
        self.selenium.find_element_by_name('profile_set-2-last_name').send_keys('2 last name 2')

        self.selenium.find_element_by_xpath('//input[@value="Save"]').click()

        try:
            # Wait for the next page to be loaded.
            self.wait_loaded_tag('body')
        except TimeoutException:
            # IE7 occasionnally returns an error "Internet Explorer cannot
            # display the webpage" and doesn't load the next page. We just
            # ignore it.
            pass

        # Check that the objects have been created in the database
        self.assertEqual(ProfileCollection.objects.all().count(), 1)
        self.assertEqual(Profile.objects.all().count(), 3)

    def test_delete_inlines(self):
        self.admin_login(username='super', password='secret')
        self.selenium.get('%s%s' % (self.live_server_url,
            '/admin/admin_inlines/profilecollection/add/'))

        # Add a few inlines
        self.selenium.find_element_by_link_text('Add another Profile').click()
        self.selenium.find_element_by_link_text('Add another Profile').click()
        self.selenium.find_element_by_link_text('Add another Profile').click()
        self.selenium.find_element_by_link_text('Add another Profile').click()
        self.failUnlessEqual(len(self.selenium.find_elements_by_css_selector(
            '#profile_set-group table tr.dynamic-profile_set')), 5)
        self.failUnlessEqual(len(self.selenium.find_elements_by_css_selector(
            'form#profilecollection_form tr.dynamic-profile_set#profile_set-0')), 1)
        self.failUnlessEqual(len(self.selenium.find_elements_by_css_selector(
            'form#profilecollection_form tr.dynamic-profile_set#profile_set-1')), 1)
        self.failUnlessEqual(len(self.selenium.find_elements_by_css_selector(
            'form#profilecollection_form tr.dynamic-profile_set#profile_set-2')), 1)
        self.failUnlessEqual(len(self.selenium.find_elements_by_css_selector(
            'form#profilecollection_form tr.dynamic-profile_set#profile_set-3')), 1)
        self.failUnlessEqual(len(self.selenium.find_elements_by_css_selector(
            'form#profilecollection_form tr.dynamic-profile_set#profile_set-4')), 1)

        # Click on a few delete buttons
        self.selenium.find_element_by_css_selector(
            'form#profilecollection_form tr.dynamic-profile_set#profile_set-1 td.delete a').click()
        self.selenium.find_element_by_css_selector(
            'form#profilecollection_form tr.dynamic-profile_set#profile_set-2 td.delete a').click()
        # Verify that they're gone and that the IDs have been re-sequenced
        self.failUnlessEqual(len(self.selenium.find_elements_by_css_selector(
            '#profile_set-group table tr.dynamic-profile_set')), 3)
        self.failUnlessEqual(len(self.selenium.find_elements_by_css_selector(
            'form#profilecollection_form tr.dynamic-profile_set#profile_set-0')), 1)
        self.failUnlessEqual(len(self.selenium.find_elements_by_css_selector(
            'form#profilecollection_form tr.dynamic-profile_set#profile_set-1')), 1)
        self.failUnlessEqual(len(self.selenium.find_elements_by_css_selector(
            'form#profilecollection_form tr.dynamic-profile_set#profile_set-2')), 1)


class SeleniumChromeTests(SeleniumFirefoxTests):
    webdriver_class = 'selenium.webdriver.chrome.webdriver.WebDriver'

class SeleniumIETests(SeleniumFirefoxTests):
    webdriver_class = 'selenium.webdriver.ie.webdriver.WebDriver'

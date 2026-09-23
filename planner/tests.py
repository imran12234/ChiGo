import os
from unittest.mock import Mock, patch

from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, override_settings

from .context_processors import google_maps
from .views import lookup_place_details, photo_proxy


class GooglePlacesTests(SimpleTestCase):
    @patch('planner.views.requests.post')
    def test_places_enrichment_uses_new_api(self, post):
        post.return_value = Mock(status_code=200)
        post.return_value.json.return_value = {'places': [{
            'location': {'latitude': 41.88, 'longitude': -87.63},
            'formattedAddress': 'Chicago, IL',
            'photos': [{'name': 'places/example/photos/photo'}],
        }]}
        result = lookup_place_details('Millennium Park', 'server-secret')
        self.assertEqual(result, {'latitude': 41.88, 'longitude': -87.63,
                                 'address': 'Chicago, IL', 'photo_name': 'places/example/photos/photo'})
        self.assertEqual(post.call_args.args[0], 'https://places.googleapis.com/v1/places:searchText')
        self.assertEqual(post.call_args.kwargs['headers']['X-Goog-Api-Key'], 'server-secret')

    @patch('planner.views.requests.post')
    def test_denied_places_request_keeps_empty_fields_and_logs_status(self, post):
        post.return_value = Mock(status_code=403)
        with self.assertLogs('planner.views', level='WARNING') as logs:
            result = lookup_place_details('Park', 'server-secret')
        self.assertEqual(result, {'latitude': 0, 'longitude': 0, 'address': '', 'photo_name': ''})
        self.assertIn('403', logs.output[0])
        self.assertNotIn('server-secret', ''.join(logs.output))

    @patch('planner.views.requests.get')
    def test_invalid_photo_path_does_not_call_google(self, get):
        response = photo_proxy(RequestFactory().get('/photo-proxy/', {'photo_name': 'places/x/../secret?key=bad'}))
        self.assertEqual(response.status_code, 400)
        get.assert_not_called()

    @patch.dict(os.environ, {'PLACES_API_KEY': ''})
    @patch('planner.views.requests.get')
    def test_missing_key_does_not_request_photo(self, get):
        response = photo_proxy(RequestFactory().get('/photo-proxy/', {'photo_name': 'places/x/photos/y'}))
        self.assertEqual(response.status_code, 503)
        get.assert_not_called()


class GoogleMapRenderingTests(SimpleTestCase):
    @override_settings(GOOGLE_MAPS_BROWSER_KEY='', GOOGLE_MAPS_MAP_ID='DEMO_MAP_ID')
    @patch.dict(os.environ, {'PLACES_API_KEY': 'private-server-secret'})
    def test_server_key_is_not_used_as_browser_key(self):
        context = google_maps(RequestFactory().get('/'))
        html = render_to_string('planner/includes/google_map.html', context)
        self.assertNotIn('private-server-secret', html)
        self.assertNotIn('maps.googleapis.com/maps/api/js', html)
        self.assertIn('View Chicago on Google Maps', html)

    @override_settings(GOOGLE_MAPS_BROWSER_KEY='public-browser-key', GOOGLE_MAPS_MAP_ID='map-id')
    def test_map_coordinates_are_json_escaped(self):
        context = google_maps(RequestFactory().get('/'))
        context['map_activities'] = [{'place': '</script><script>alert(1)</script>', 'latitude': 41.88, 'longitude': -87.63}]
        html = render_to_string('planner/includes/google_map.html', context)
        self.assertNotIn('</script><script>alert(1)</script>', html)
        self.assertIn('maps.googleapis.com/maps/api/js?key=public-browser-key', html)
        self.assertNotIn('openstreetmap', html)

    def test_missing_activity_photo_does_not_render_empty_proxy_request(self):
        html = render_to_string('planner/activity.html', {'activities': [{
            'id': 1, 'place': 'Park', 'description': 'A park', 'photo_name': '',
        }], 'day': 1, 'total_days': 1})
        self.assertNotIn('photo-proxy/?photo_name=', html)
        self.assertIn('Photo unavailable', html)


class PasswordResetPresentationTests(SimpleTestCase):
    def test_invalid_reset_link_offers_recovery_without_password_form(self):
        html = render_to_string('password_reset/confirm.html', {'validlink': False})
        self.assertIn('Request a new link', html)
        self.assertNotIn('type="password"', html)

    def test_new_password_fields_do_not_echo_values(self):
        from django.contrib.auth.forms import SetPasswordForm
        from django.contrib.auth.models import User
        form = SetPasswordForm(User(username='preview'), initial={
            'new_password1': 'do-not-render-password',
            'new_password2': 'do-not-render-password',
        })
        html = render_to_string('password_reset/confirm.html', {
            'validlink': True, 'form': form, 'csrf_token': 'test-only',
        })
        self.assertNotIn('do-not-render-password', html)
        self.assertEqual(html.count('autocomplete="new-password"'), 2)
        self.assertIn('Save new password', html)

    def test_email_error_is_linked_to_its_field(self):
        from django.contrib.auth.forms import PasswordResetForm
        form = PasswordResetForm({'email': 'invalid'})
        html = render_to_string('password_reset/form.html', {
            'form': form, 'csrf_token': 'test-only',
        })
        self.assertIn('aria-invalid="true"', html)
        self.assertIn('aria-describedby="email-error"', html)
        self.assertIn('Enter a valid email address.', html)
        self.assertIn('Send reset link', html)

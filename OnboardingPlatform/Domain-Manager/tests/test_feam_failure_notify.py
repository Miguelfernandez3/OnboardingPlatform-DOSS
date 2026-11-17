"""Tests for admin notifications when FEAM infrastructure failures occur."""
import json
import os
import unittest
from unittest.mock import MagicMock, patch

from services.feam_service import FEAMService, _is_infrastructure_failure
from services.notifications import feam_health
from services.notifications.service import NotificationService, _feam_dedup_bucket


class _AdminUser:
    def __init__(self, user_id: int, role: str = 'admin', language: str = 'es'):
        self.id = user_id
        self.role = role
        self.language = language
        self.in_app_notifications_enabled = True
        self.telegram_enabled = False
        self.telegram_chat_id = None


class _RegularUser:
    def __init__(self, user_id: int):
        self.id = user_id
        self.role = 'user'
        self.language = 'es'
        self.in_app_notifications_enabled = True


class _DummyFEAMClient:
    def check_pin(self, pin=None):
        return {"status": "ok"}

    def call_resource_server(self, **kwargs):
        return {
            "ok": False,
            "status_code": 503,
            "error": "service unavailable",
            "attempts": [{"attempt": 1, "elapsed_ms": 1.0, "status_code": 503, "ok": False, "error": "service unavailable"}],
        }

    def get_functions_own(self):
        return {
            "ok": False,
            "status_code": None,
            "error": "connection_error: refused",
            "attempts": [{"attempt": 1, "elapsed_ms": 1.0, "status_code": None, "ok": False, "error": "connection_error: refused"}],
        }


class _FakeRedis:
    def __init__(self):
        self.values = {}
        self.set_calls = []
        self.delete_calls = []

    def set(self, key, value, ex=None, nx=False):
        self.set_calls.append({"key": key, "value": value, "ex": ex, "nx": nx})
        if nx and key in self.values:
            return None
        self.values[key] = value
        return True

    def get(self, key):
        return self.values.get(key)

    def delete(self, key):
        self.delete_calls.append(key)
        existed = key in self.values
        self.values.pop(key, None)
        return 1 if existed else 0


class InfrastructureFailureClassifierTests(unittest.TestCase):
    def test_connection_error_is_infrastructure(self):
        self.assertTrue(_is_infrastructure_failure({"ok": False, "status_code": None}))

    def test_503_is_infrastructure(self):
        self.assertTrue(_is_infrastructure_failure({"ok": False, "status_code": 503}))

    def test_408_is_infrastructure(self):
        self.assertTrue(_is_infrastructure_failure({"ok": False, "status_code": 408}))

    def test_404_is_not_infrastructure(self):
        self.assertFalse(_is_infrastructure_failure({"ok": False, "status_code": 404}))

    def test_ok_response_is_not_infrastructure(self):
        self.assertFalse(_is_infrastructure_failure({"ok": True, "status_code": 200}))


class NotifyFeamUnavailableTests(unittest.TestCase):
    def setUp(self):
        self._old_notifications = os.environ.get('NOTIFICATIONS_ENABLED')
        self._old_dedup_hours = os.environ.get('FEAM_FAILURE_NOTIFY_DEDUP_HOURS')
        os.environ['NOTIFICATIONS_ENABLED'] = 'true'
        os.environ['FEAM_FAILURE_NOTIFY_DEDUP_HOURS'] = '12'

    def tearDown(self):
        if self._old_notifications is None:
            os.environ.pop('NOTIFICATIONS_ENABLED', None)
        else:
            os.environ['NOTIFICATIONS_ENABLED'] = self._old_notifications
        if self._old_dedup_hours is None:
            os.environ.pop('FEAM_FAILURE_NOTIFY_DEDUP_HOURS', None)
        else:
            os.environ['FEAM_FAILURE_NOTIFY_DEDUP_HOURS'] = self._old_dedup_hours

    def test_notifies_eligible_admins_only(self):
        db = MagicMock()
        admin = _AdminUser(1)
        db.getUsersEligibleForAdminNotifications.return_value = [admin]
        db.getNotificationByDedupKey.return_value = None
        created_row = MagicMock(id=99)
        db.createNotification.return_value = created_row

        with patch('services.notifications.service.enqueue_notification_delivery', return_value=True):
            NotificationService(db).notify_feam_unavailable(
                endpoint='callResourceServer',
                error_message='service unavailable',
                status_code=503,
            )

        db.getUsersEligibleForAdminNotifications.assert_called_once()
        db.createNotification.assert_called_once()
        kwargs = db.createNotification.call_args.kwargs
        self.assertEqual(kwargs['user_id'], 1)
        self.assertEqual(kwargs['notification_type'], 'feam_unavailable')
        self.assertIsNone(kwargs['device_id'])
        self.assertIn(':feam_unavailable:b', kwargs['deduplication_key'])

    def test_dedup_same_bucket_skips_second_notification(self):
        db = MagicMock()
        admin = _AdminUser(1)
        db.getUsersEligibleForAdminNotifications.return_value = [admin]
        bucket = _feam_dedup_bucket()
        db.getNotificationByDedupKey.return_value = MagicMock(id=1)

        with patch('services.notifications.service.enqueue_notification_delivery', return_value=True):
            NotificationService(db).notify_feam_unavailable(
                endpoint='getFunctionsOwn',
                error_message='connection refused',
                status_code=None,
            )

        db.getNotificationByDedupKey.assert_called_with(f'{admin.id}:feam_unavailable:b{bucket}')
        db.createNotification.assert_not_called()

    def test_dedup_different_bucket_creates_new_notification(self):
        db = MagicMock()
        admin = _AdminUser(2)
        db.getUsersEligibleForAdminNotifications.return_value = [admin]
        db.getNotificationByDedupKey.return_value = None
        db.createNotification.return_value = MagicMock(id=100)

        with patch('services.notifications.service._feam_dedup_bucket', return_value=99999):
            with patch('services.notifications.service.enqueue_notification_delivery', return_value=True):
                NotificationService(db).notify_feam_unavailable(
                    endpoint='callResourceServer',
                    error_message='timeout',
                    status_code=504,
                )

        dedup = db.createNotification.call_args.kwargs['deduplication_key']
        self.assertEqual(dedup, '2:feam_unavailable:b99999')

    def test_skips_when_notifications_disabled(self):
        os.environ['NOTIFICATIONS_ENABLED'] = 'false'
        db = MagicMock()
        NotificationService(db).notify_feam_unavailable(
            endpoint='callResourceServer',
            error_message='down',
            status_code=500,
        )
        db.getUsersEligibleForAdminNotifications.assert_not_called()


class FEAMServiceNotifyHookTests(unittest.TestCase):
    def test_execute_operation_records_infrastructure_failure_on_503(self):
        db = MagicMock()
        client = _DummyFEAMClient()
        service = FEAMService(client, db)

        with patch('services.notifications.feam_health.record_infrastructure_failure') as record_failure:
            with self.assertRaises(RuntimeError):
                service.execute_operation(
                    function_id='1bfae6a6-a268-4d90-ad87-3b8817f0852c',
                    operation_id='1bfae6a6-b492-4267-9ef5-92b15f22a394',
                )
            record_failure.assert_called_once()
            kwargs = record_failure.call_args.kwargs
            self.assertEqual(kwargs['endpoint'], 'callResourceServer')
            self.assertEqual(kwargs['status_code'], 503)
            self.assertEqual(kwargs['db'], db)

    def test_refresh_catalog_records_infrastructure_failure_on_connection_error(self):
        db = MagicMock()
        client = _DummyFEAMClient()
        service = FEAMService(client, db)

        with patch('services.notifications.feam_health.record_infrastructure_failure') as record_failure:
            with self.assertRaises(RuntimeError):
                service.refresh_catalog()
            record_failure.assert_called_once()
            kwargs = record_failure.call_args.kwargs
            self.assertEqual(kwargs['endpoint'], 'getFunctionsOwn')
            self.assertIsNone(kwargs['status_code'])
            self.assertEqual(kwargs['db'], db)

    def test_404_does_not_notify(self):
        db = MagicMock()
        client = _DummyFEAMClient()

        def call_404(**kwargs):
            return {
                "ok": False,
                "status_code": 404,
                "error": "not found",
                "attempts": [{"attempt": 1, "elapsed_ms": 1.0, "status_code": 404, "ok": False, "error": "not found"}],
            }

        client.call_resource_server = call_404
        service = FEAMService(client, db)

        with patch('services.notifications.feam_health.record_infrastructure_failure') as record_failure:
            with self.assertRaises(RuntimeError):
                service.execute_operation(
                    function_id='1bfae6a6-a268-4d90-ad87-3b8817f0852c',
                    operation_id='1bfae6a6-b492-4267-9ef5-92b15f22a394',
                )
            record_failure.assert_not_called()

    def test_execute_operation_records_recovery_after_completed_call_resource_server(self):
        db = MagicMock()
        client = _DummyFEAMClient()

        def call_ok(**kwargs):
            return {"ok": True, "status_code": 200, "body": {"status": "ok"}, "attempts": []}

        client.call_resource_server = call_ok
        service = FEAMService(client, db)

        with patch('services.notifications.feam_health.record_infrastructure_success') as record_success:
            service.execute_operation(
                function_id='1bfae6a6-a268-4d90-ad87-3b8817f0852c',
                operation_id='1bfae6a6-b492-4267-9ef5-92b15f22a394',
            )

        record_success.assert_called_once_with('callResourceServer')

    def test_refresh_catalog_records_recovery_after_completed_get_functions_own(self):
        db = MagicMock()
        client = _DummyFEAMClient()

        def get_functions_ok():
            return {"ok": True, "status_code": 200, "body": {"status": "ok"}, "attempts": []}

        client.get_functions_own = get_functions_ok
        service = FEAMService(client, db)

        with patch('services.notifications.feam_health.record_infrastructure_success') as record_success:
            service.refresh_catalog()

        record_success.assert_called_once_with('getFunctionsOwn')


class FeamHealthGraceTests(unittest.TestCase):
    def setUp(self):
        self._old_grace = os.environ.get('FEAM_FAILURE_NOTIFY_GRACE_MINUTES')
        os.environ['FEAM_FAILURE_NOTIFY_GRACE_MINUTES'] = '5'

    def tearDown(self):
        if self._old_grace is None:
            os.environ.pop('FEAM_FAILURE_NOTIFY_GRACE_MINUTES', None)
        else:
            os.environ['FEAM_FAILURE_NOTIFY_GRACE_MINUTES'] = self._old_grace

    def test_failure_creates_pending_state_and_defers_notification(self):
        redis_client = _FakeRedis()

        with patch('services.notifications.feam_health._redis_client', return_value=redis_client):
            with patch('services.notifications.feam_health._enqueue_pending_alert') as enqueue_alert:
                with patch('services.notifications.feam_health._notify_feam_unavailable') as notify:
                    created = feam_health.record_infrastructure_failure(
                        endpoint='callResourceServer',
                        error_message='service unavailable',
                        status_code=503,
                        db=MagicMock(),
                    )

        self.assertTrue(created)
        enqueue_alert.assert_called_once_with(300)
        notify.assert_not_called()
        payload = json.loads(redis_client.get(feam_health.PENDING_ALERT_KEY))
        self.assertEqual(payload['endpoint'], 'callResourceServer')
        self.assertEqual(payload['status_code'], 503)

    def test_success_clears_pending_state_and_job_does_not_notify(self):
        redis_client = _FakeRedis()
        redis_client.values[feam_health.PENDING_ALERT_KEY] = json.dumps(
            {
                "first_failure_at": 0,
                "endpoint": "callResourceServer",
                "error_message": "service unavailable",
                "status_code": 503,
            }
        )

        with patch('services.notifications.feam_health._redis_client', return_value=redis_client):
            self.assertTrue(feam_health.record_infrastructure_success('callResourceServer'))
            with patch('services.notifications.feam_health._notify_feam_unavailable') as notify:
                processed = feam_health.process_pending_alert(db=MagicMock())

        self.assertFalse(processed)
        notify.assert_not_called()
        self.assertIsNone(redis_client.get(feam_health.PENDING_ALERT_KEY))

    def test_job_after_grace_notifies_once_and_clears_state(self):
        redis_client = _FakeRedis()
        redis_client.values[feam_health.PENDING_ALERT_KEY] = json.dumps(
            {
                "first_failure_at": 0,
                "endpoint": "getFunctionsOwn",
                "error_message": "connection refused",
                "status_code": None,
            }
        )
        db = MagicMock()

        with patch('services.notifications.feam_health._redis_client', return_value=redis_client):
            with patch('services.notifications.feam_health._notify_feam_unavailable') as notify:
                processed = feam_health.process_pending_alert(db=db)

        self.assertTrue(processed)
        notify.assert_called_once_with(
            endpoint='getFunctionsOwn',
            error_message='connection refused',
            status_code=None,
            db=db,
        )
        self.assertIsNone(redis_client.get(feam_health.PENDING_ALERT_KEY))

    def test_two_failures_in_grace_window_schedule_one_job(self):
        redis_client = _FakeRedis()

        with patch('services.notifications.feam_health._redis_client', return_value=redis_client):
            with patch('services.notifications.feam_health._enqueue_pending_alert') as enqueue_alert:
                feam_health.record_infrastructure_failure(
                    endpoint='callResourceServer',
                    error_message='first failure',
                    status_code=503,
                )
                first_payload = json.loads(redis_client.get(feam_health.PENDING_ALERT_KEY))
                feam_health.record_infrastructure_failure(
                    endpoint='getFunctionsOwn',
                    error_message='second failure',
                    status_code=None,
                )

        second_payload = json.loads(redis_client.get(feam_health.PENDING_ALERT_KEY))
        enqueue_alert.assert_called_once_with(300)
        self.assertEqual(second_payload['first_failure_at'], first_payload['first_failure_at'])
        self.assertEqual(second_payload['error_message'], 'second failure')

    def test_grace_zero_notifies_immediately_without_redis_or_queue(self):
        os.environ['FEAM_FAILURE_NOTIFY_GRACE_MINUTES'] = '0'
        db = MagicMock()

        with patch('services.notifications.feam_health._redis_client') as redis_client:
            with patch('services.notifications.feam_health._enqueue_pending_alert') as enqueue_alert:
                with patch('services.notifications.feam_health._notify_feam_unavailable') as notify:
                    created = feam_health.record_infrastructure_failure(
                        endpoint='callResourceServer',
                        error_message='timeout',
                        status_code=504,
                        db=db,
                    )

        self.assertTrue(created)
        redis_client.assert_not_called()
        enqueue_alert.assert_not_called()
        notify.assert_called_once_with(
            endpoint='callResourceServer',
            error_message='timeout',
            status_code=504,
            db=db,
        )


if __name__ == '__main__':
    unittest.main()

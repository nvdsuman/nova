#    Copyright 2013 IBM Corp.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import datetime

from nova import context
from nova import db
from nova.objects import migration
from nova.openstack.common import timeutils
from nova.tests import fake_instance
from nova.tests.objects import test_objects


NOW = timeutils.utcnow().replace(microsecond=0)
fake_migration = {
    'created_at': NOW,
    'updated_at': None,
    'deleted_at': None,
    'deleted': False,
    'id': 123,
    'source_compute': 'compute-source',
    'dest_compute': 'compute-dest',
    'source_node': 'node-source',
    'dest_node': 'node-dest',
    'dest_host': 'host-dest',
    'old_instance_type_id': 42,
    'new_instance_type_id': 84,
    'instance_uuid': 'fake-uuid',
    'status': 'migrating',
}


class _TestMigrationObject(object):
    def _compare(self, obj, db_obj):
        for key in obj.fields:
            obj_val = obj[key]
            if isinstance(obj_val, datetime.datetime):
                obj_val = obj_val.replace(tzinfo=None)
            db_val = db_obj[key]
            self.assertEqual(db_val, obj_val)

    def test_get_by_id(self):
        ctxt = context.get_admin_context()
        self.mox.StubOutWithMock(db, 'migration_get')
        db.migration_get(ctxt, fake_migration['id']).AndReturn(fake_migration)
        self.mox.ReplayAll()
        mig = migration.Migration.get_by_id(ctxt, fake_migration['id'])
        self._compare(mig, fake_migration)

    def test_get_by_instance_and_status(self):
        ctxt = context.get_admin_context()
        self.mox.StubOutWithMock(db, 'migration_get_by_instance_and_status')
        db.migration_get_by_instance_and_status(ctxt,
                                                fake_migration['id'],
                                                'migrating'
                                                ).AndReturn(fake_migration)
        self.mox.ReplayAll()
        mig = migration.Migration.get_by_instance_and_status(
            ctxt, fake_migration['id'], 'migrating')
        self._compare(mig, fake_migration)

    def test_create(self):
        ctxt = context.get_admin_context()
        self.mox.StubOutWithMock(db, 'migration_create')
        db.migration_create(ctxt, {'source_compute': 'foo'}).AndReturn(
            fake_migration)
        self.mox.ReplayAll()
        mig = migration.Migration()
        mig.source_compute = 'foo'
        mig.create(ctxt)
        self.assertEqual(fake_migration['dest_compute'], mig.dest_compute)

    def test_save(self):
        ctxt = context.get_admin_context()
        self.mox.StubOutWithMock(db, 'migration_update')
        db.migration_update(ctxt, 123, {'source_compute': 'foo'}
                            ).AndReturn(fake_migration)
        self.mox.ReplayAll()
        mig = migration.Migration()
        mig.id = 123
        mig.source_compute = 'foo'
        mig.save(ctxt)
        self.assertEqual(fake_migration['dest_compute'], mig.dest_compute)

    def test_instance(self):
        ctxt = context.get_admin_context()
        fake_inst = fake_instance.fake_db_instance()
        self.mox.StubOutWithMock(db, 'instance_get_by_uuid')
        db.instance_get_by_uuid(ctxt, fake_migration['instance_uuid'],
                                columns_to_join=[]
                                ).AndReturn(fake_inst)
        mig = migration.Migration._from_db_object(ctxt,
                                                  migration.Migration(),
                                                  fake_migration)
        mig._context = ctxt
        self.mox.ReplayAll()
        self.assertEqual(mig.instance.host, fake_inst['host'])

    def test_get_unconfirmed_by_dest_compute(self):
        ctxt = context.get_admin_context()
        db_migrations = [fake_migration, dict(fake_migration, id=456)]
        self.mox.StubOutWithMock(
            db, 'migration_get_unconfirmed_by_dest_compute')
        db.migration_get_unconfirmed_by_dest_compute(
            ctxt, 'window', 'foo').AndReturn(db_migrations)
        self.mox.ReplayAll()
        migrations = (
            migration.MigrationList.get_unconfirmed_by_dest_compute(
                ctxt, 'window', 'foo'))
        self.assertEqual(2, len(migrations))
        for index, db_migration in enumerate(db_migrations):
            self._compare(migrations[index], db_migration)

    def test_get_in_progress_by_host_and_node(self):
        ctxt = context.get_admin_context()
        db_migrations = [fake_migration, dict(fake_migration, id=456)]
        self.mox.StubOutWithMock(
            db, 'migration_get_in_progress_by_host_and_node')
        db.migration_get_in_progress_by_host_and_node(
            ctxt, 'host', 'node').AndReturn(db_migrations)
        self.mox.ReplayAll()
        migrations = (
            migration.MigrationList.get_in_progress_by_host_and_node(
                ctxt, 'host', 'node'))
        self.assertEqual(2, len(migrations))
        for index, db_migration in enumerate(db_migrations):
            self._compare(migrations[index], db_migration)

    def test_get_by_filters(self):
        ctxt = context.get_admin_context()
        db_migrations = [fake_migration, dict(fake_migration, id=456)]
        self.mox.StubOutWithMock(
            db, 'migration_get_all_by_filters')
        filters = {'foo': 'bar'}
        db.migration_get_all_by_filters(ctxt, filters).AndReturn(db_migrations)
        self.mox.ReplayAll()
        migrations = migration.MigrationList.get_by_filters(ctxt, filters)
        self.assertEqual(2, len(migrations))
        for index, db_migration in enumerate(db_migrations):
            self._compare(migrations[index], db_migration)


class TestMigrationObject(test_objects._LocalTest,
                          _TestMigrationObject):
    pass


class TestRemoteMigrationObject(test_objects._RemoteTest,
                                _TestMigrationObject):
    pass

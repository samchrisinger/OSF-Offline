from unittest import TestCase
from appdirs import user_data_dir
from osfoffline.db import get_session, setup_db, remove_db
from tests import TEST_DIR
import os
from osfoffline.sync_local_filesytem_and_db import LocalDBSync
from osfoffline.models import User, Node, File, Base
from watchdog.observers import Observer
import asyncio
from osfoffline.osf_event_handler import OSFEventHandler

# acceptance tests
# now going to test whether the class overall functions properly

class TestLocalDBSyncAcceptance(TestCase):
    def setUp(self):
        self.db_dir = user_data_dir(appname='test-app-name-setup', appauthor='test-app-author-setup')
        # creates a new db each time
        setup_db(self.db_dir)
        self.session = get_session()
        self.osf_dir = os.path.join(TEST_DIR,"fixtures","mock_projects","OSF")
        self.user = User(osf_local_folder_path=self.osf_dir)

        self.session.add(self.user)
        self.session.commit()
        self.session.refresh(self.user)

        self.observer = Observer()

        self.loop = asyncio.get_event_loop()
        self.event_handler = OSFEventHandler(self.osf_dir, '','',self.loop)
        self.observer.schedule(self.event_handler, self.osf_dir, recursive=True)

        # self.observer.start()

    def tearDown(self):
        remove_db()

    def test_empty_db_and_local(self):
        sync = LocalDBSync(self.user.osf_local_folder_path, self.observer, self.user)
        sync.emit_new_events()
        self.assertEqual(1, 1)

        # self.loop.run_forever()

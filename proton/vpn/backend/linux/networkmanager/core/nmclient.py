import logging
from concurrent.futures import Future
from threading import Thread, Lock
from typing import Callable, Optional

import gi
gi.require_version("NM", "1.0")  # noqa: required before importing NM module
from gi.repository import NM, GLib

from proton.vpn.connection.exceptions import VPNConnectionError

logger = logging.getLogger(__name__)


class NMClient:
    _lock = Lock()
    _main_context = None
    _nm_client = None

    def __init__(self):
        cls = type(self)
        with cls._lock:
            if not cls._nm_client:
                self._initialize_nm_client_singleton()

    def _initialize_nm_client_singleton(self):
        cls = type(self)
        cls._main_context = GLib.MainContext()
        cls._nm_client = NM.Client()
        # Setting daemon=True when creating the thread makes that this thread
        # exits abruptly when the python process exits. It would be better to
        # exit the thread running the main loop calling self._main_loop.quit().
        Thread(target=cls._run_main_loop, daemon=True).start()

        callback, future = self.create_nmcli_callback(
            finish_method_name="new_finish"
        )

        def new_async():
            cls._assert_running_on_main_loop_thread()
            self._nm_client.new_async(cancellable=None, callback=callback, user_data=None)

        cls._run_on_main_loop_thread(new_async)
        cls._nm_client = future.result()

    @classmethod
    def _run_main_loop(cls):
        main_loop = GLib.MainLoop(cls._main_context)
        cls._main_context.push_thread_default()
        main_loop.run()

    @classmethod
    def _assert_running_on_main_loop_thread(cls):
        """
        This method asserts that the thread running it is the one iterating
        GLib's main loop.

        It's useful to call this method at the beginning of any code block
        that's supposed to run in GLib's main loop, to avoid hard-to-debug
        issues.

        For more info:
        https://developer.gnome.org/documentation/tutorials/main-contexts.html#checking-threading
        """
        assert cls._main_context.is_owner()

    @classmethod
    def _run_on_main_loop_thread(cls, function):
        cls._main_context.invoke_full(priority=GLib.PRIORITY_DEFAULT, function=function)

    def create_nmcli_callback(self, finish_method_name: str) -> (Callable, Future):
        future = Future()
        future.set_running_or_notify_cancel()

        def callback(source_object, res, userdata):
            self._assert_running_on_main_loop_thread()
            try:
                # On errors, according to the docs, the callback can be called
                # with source_object/res set to None.
                # https://lazka.github.io/pgi-docs/index.html#NM-1.0/classes/Client.html#NM.Client.new_async
                if not source_object or not res:

                    raise VPNConnectionError(
                        f"An unexpected error occurred initializing NMClient: "
                        f"source_object = {source_object}, res = {res}."
                    )

                result = getattr(source_object, finish_method_name)(res)

                # According to the docs, None is returned on errors
                # https://lazka.github.io/pgi-docs/index.html#NM-1.0/classes/Client.html#NM.Client.new_finish
                if not result:
                    raise VPNConnectionError(
                        "An unexpected error occurred initializing NMCLient"
                    )

                future.set_result(result)
            except BaseException as e:
                future.set_exception(e)

        return callback, future

    def commit_changes_async(
            self, new_connection: NM.RemoteConnection
    ) -> Future:
        callback, future = self.create_nmcli_callback(
            finish_method_name="commit_changes_finish"
        )

        def commit_changes_async():
            self._assert_running_on_main_loop_thread()
            new_connection.commit_changes_async(
                True,
                None,
                callback,
                None
            )

        self._run_on_main_loop_thread(commit_changes_async)
        return future

    def add_connection_async(self, connection: NM.Connection) -> Future:
        callback, future = self.create_nmcli_callback(
            finish_method_name="add_connection_finish"
        )

        def add_connection_async():
            self._assert_running_on_main_loop_thread()
            self._nm_client.add_connection_async(
                connection,
                True,
                None,
                callback,
                None
            )

        self._run_on_main_loop_thread(add_connection_async)
        return future

    def start_connection_async(self, connection: NM.Connection) -> Future:
        """Start ProtonVPN connection."""
        callback, future = self.create_nmcli_callback(
            finish_method_name="activate_connection_finish"
        )

        def activate_connection_async():
            self._assert_running_on_main_loop_thread()
            self._nm_client.activate_connection_async(
                connection,
                None,
                None,
                None,
                callback,
                None
            )

        self._run_on_main_loop_thread(activate_connection_async)
        return future

    def remove_connection_async(
            self, connection: NM.RemoteConnection
    ) -> Future:
        callback, future = self.create_nmcli_callback(
            finish_method_name="delete_finish"
        )

        def delete_async():
            self._assert_running_on_main_loop_thread()
            connection.delete_async(
                None,
                callback,
                None
            )

        self._run_on_main_loop_thread(delete_async)
        return future

    def get_active_connection(self, uuid: str) -> Optional[NM.ActiveConnection]:
        active_connections = self._nm_client.get_active_connections()

        for connection in active_connections:
            if connection.get_uuid() == uuid:
                return connection

        return None

    def get_connection(self, uuid: str) -> Optional[NM.RemoteConnection]:
        return self._nm_client.get_connection_by_uuid(uuid)

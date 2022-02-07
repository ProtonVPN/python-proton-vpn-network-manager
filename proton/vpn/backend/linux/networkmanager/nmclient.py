import gi
gi.require_version("NM", "1.0")
from gi.repository import NM, GLib


class NMClient:
    _nm_client = NM.Client.new(None)
    _main_loop = GLib.MainLoop()
    failure = None

    @property
    def nm_client(self):
        return self._nm_client

    def _commit_changes_async(self, new_connection):
        new_connection.commit_changes_async(
            True,
            None,
            self.__dynamic_callback,
            dict(
                callback_type="commit",
                conn_name=new_connection.get_id(),
            )
        )
        self._main_loop.run()
        if NMClient.failure is not None:
            raise NMClient.failure

    def _add_connection_async(self, connection):
        self._nm_client.add_connection_async(
            connection,
            True,
            None,
            self.__dynamic_callback,
            dict(
                callback_type="add",
                conn_name=connection.get_id(),
            )
        )
        self._main_loop.run()
        if NMClient.failure is not None:
            raise NMClient.failure

    def _start_connection_async(self, connection):
        """Start ProtonVPN connection."""
        self._nm_client.activate_connection_async(
            connection,
            None,
            None,
            None,
            self.__dynamic_callback,
            dict(
                callback_type="start",
                conn_name=connection.get_id()
            )
        )
        self._main_loop.run()
        if NMClient.failure is not None:
            raise NMClient.failure

    def _remove_connection_async(self, connection):
        try:
            self.stop_connection_async(connection)
        except: # noqa
            pass

        connection.delete_async(
            None,
            self.__dynamic_callback,
            dict(
                callback_type="remove",
                conn_name=connection.get_id()
            )
        )
        self._main_loop.run()
        if NMClient.failure is not None:
            raise NMClient.failure

    def _stop_connection_async(self, connection):
        """Stop ProtonVPN connection.

        Args(optional):
            client (NM.nm_client): new NetworkManager Client object
        """
        self._nm_client.deactivate_connection_async(
            connection,
            None,
            self.__dynamic_callback,
            dict(
                callback_type="stop",
                conn_name=connection.get_id()
            )
        )
        self._main_loop.run()
        if NMClient.failure is not None:
            raise NMClient.failure

    def __dynamic_callback(self, client, result, data):
        """Dynamic callback method.

        Args:
            client (NM.nm_client): nm client object
            result (Gio.AsyncResult): function
            data (dict): optional extra data
        """
        callback_type = data.get("callback_type")
        try:
            callback_type_dict = dict(
                remove=dict(
                    finish_function=NM.Client.delete_finish,
                    msg="remove"
                )
            )
        except AttributeError:
            callback_type_dict = dict(
                add=dict(
                    finish_function=NM.Client.add_connection_finish
                ),
                start=dict(
                    finish_function=NM.Client.activate_connection_finish
                ),
                stop=dict(
                    finish_function=NM.Client.deactivate_connection_finish
                ),
                commit=dict(
                    finish_function=NM.RemoteConnection.commit_changes_finish
                )
            )

        try:
            callback_type_dict[
                callback_type
            ]["finish_function"](client, result)
        except KeyError:
            pass
        except Exception as e:
            NMClient.failure = e

        self._main_loop.quit()

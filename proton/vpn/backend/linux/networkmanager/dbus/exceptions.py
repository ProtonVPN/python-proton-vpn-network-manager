class ProtonDbusException(Exception):
    """Base class for dbus  python wrapper exceptions"""
    def __init__(self, message, additional_context=None):
        self.message = message
        self.additional_context = additional_context
        super().__init__(self.message)

class MetaApiError(Exception):
    pass


class RequestError(MetaApiError):
    def __init__(self, response: dict, message: str = ""):
        self.__response = response
        self.__message = message or "RequestError"

        super().__init__(message)

    def __str__(self):
        return f"{self.__message}: {self.__response}"


class ServerError(RequestError):
    def __init__(self, response: dict):
        super().__init__(response, "ServerError")


class TooManyRequestsError(RequestError):
    def __init__(self, response: dict):
        super().__init__(response, "TooManyRequestsError")


class AuthenticationError(RequestError):
    def __init__(self, response: dict):
        super().__init__(response, "AuthenticationError")


class NotFoundError(RequestError):
    def __init__(self, response: dict):
        super().__init__(response, "NotFoundError")

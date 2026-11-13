from gquarium.web.responses import JsonResponse
from gquarium.web.router import ROUTES, Router


def stub(name):
    def controller(request, services):
        return JsonResponse({"who": name})

    return controller


def test_resolves_the_matching_controller():
    """
    validate (method, path) selects its controller
    """
    a, b = stub("a"), stub("b")
    router = Router({("GET", "/a"): a, ("GET", "/b"): b})
    assert router.resolve("GET", "/a") is a and router.resolve("GET", "/b") is b


def test_unknown_path_is_404():
    """
    validate unknown paths give a 404 response
    """
    response = Router({("GET", "/a"): stub("a")}).resolve("GET", "/zzz")(None, None)
    assert response.status == 404


def test_wrong_method_is_405_with_allow_header():
    """
    validate a known path with the wrong method gives 405 and lists the allowed methods
    """
    router = Router({("GET", "/a"): stub("a"), ("POST", "/a"): stub("a2")})
    response = router.resolve("DELETE", "/a")(None, None)
    assert response.status == 405 and response.headers["Allow"] == "GET, POST"


def test_default_routes():
    """
    validate the shipped route table
    """
    assert set(ROUTES) == {("GET", "/health"), ("GET", "/now-playing"), ("GET", "/stream.ts")}

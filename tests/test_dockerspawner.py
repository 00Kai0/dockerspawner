"""Tests for DockerSpawner class"""

import json

import pytest

from jupyterhub.tests.test_api import add_user, api_request
from jupyterhub.tests.mocking import public_url
from jupyterhub.tests.utils import async_requests
from jupyterhub.utils import url_path_join

from dockerspawner import DockerSpawner

pytestmark = pytest.mark.usefixtures("dockerspawner")


@pytest.mark.gen_test
def test_start_stop(app):
    name = "has@"
    add_user(app.db, app, name=name)
    user = app.users[name]
    assert isinstance(user.spawner, DockerSpawner)
    token = user.new_api_token()
    # start the server
    r = yield api_request(app, "users", name, "server", method="post")
    while r.status_code == 202:
        # request again
        r = yield api_request(app, "users", name, "server", method="post")
    assert r.status_code == 201, r.text
    url = url_path_join(public_url(app, user), "api/status")
    r = yield async_requests.get(url, headers={"Authorization": "token %s" % token})
    assert r.url == url
    r.raise_for_status()
    print(r.text)
    assert "kernels" in r.json()


@pytest.mark.gen_test
@pytest.mark.parametrize("image", ["0.8", "0.9", "nomatch"])
def test_image_whitelist(app, image):
    name = "checker"
    add_user(app.db, app, name=name)
    user = app.users[name]
    assert isinstance(user.spawner, DockerSpawner)
    user.spawner.remove_containers = True
    user.spawner.image_whitelist = {
        "0.9": "jupyterhub/singleuser:0.9",
        "0.8": "jupyterhub/singleuser:0.8",
    }
    token = user.new_api_token()
    # start the server
    r = yield api_request(
        app, "users", name, "server", method="post", data=json.dumps({"image": image})
    )
    if image not in user.spawner.image_whitelist:
        with pytest.raises(Exception):
            r.raise_for_status()
        return
    while r.status_code == 202:
        # request again
        r = yield api_request(app, "users", name, "server", method="post")
    assert r.status_code == 201, r.text
    url = url_path_join(public_url(app, user), "api/status")
    r = yield async_requests.get(url, headers={"Authorization": "token %s" % token})
    r.raise_for_status()
    assert r.headers['x-jupyterhub-version'].startswith(image)
    r = yield api_request(
        app, "users", name, "server", method="delete",
    )
    r.raise_for_status()

import pytest
from django.contrib.auth.models import User

from tenancy.models import Business, Profile


@pytest.fixture
def two_businesses(db):
    a = Business.objects.create(name="Cafe Uno", kind="cafe")
    b = Business.objects.create(name="Resto Dos", kind="restaurant")
    return a, b


@pytest.mark.django_db
def test_owner_sees_only_their_business(two_businesses):
    a, b = two_businesses
    user = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=user, role="owner", business=a)

    visible = Business.objects.for_user(user)

    assert list(visible) == [a]
    assert b not in visible


@pytest.mark.django_db
def test_admin_sees_all_businesses(two_businesses):
    a, b = two_businesses
    user = User.objects.create_user("root", password="x")
    Profile.objects.create(user=user, role="admin")

    visible = Business.objects.for_user(user)

    assert set(visible) == {a, b}


@pytest.mark.django_db
def test_user_without_profile_sees_nothing(two_businesses):
    user = User.objects.create_user("nadie", password="x")

    assert list(Business.objects.for_user(user)) == []


@pytest.mark.django_db
def test_is_admin_flag(db):
    owner = User.objects.create_user("o", password="x")
    Profile.objects.create(user=owner, role="owner",
                           business=Business.objects.create(name="X", kind="cafe"))
    assert owner.profile.is_admin is False

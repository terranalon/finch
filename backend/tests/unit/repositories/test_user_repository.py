"""Tests for UserRepository."""

from app.services.repositories.user_repository import UserRepository


class TestUserRepository:
    """Test cases for UserRepository."""

    def test_find_by_id_returns_user(self, db, test_user):
        """Should return user when ID exists."""
        repo = UserRepository(db)
        user = repo.find_by_id(test_user.id)
        assert user is not None
        assert user.id == test_user.id

    def test_find_by_id_returns_none_for_missing(self, db):
        """Should return None when ID does not exist."""
        repo = UserRepository(db)
        user = repo.find_by_id("nonexistent-uuid-12345")
        assert user is None

    def test_find_by_email_returns_user(self, db, test_user):
        """Should return user when email exists."""
        repo = UserRepository(db)
        user = repo.find_by_email("test@example.com")
        assert user is not None
        assert user.email == "test@example.com"

    def test_find_by_email_returns_none_for_missing(self, db):
        """Should return None when email does not exist."""
        repo = UserRepository(db)
        user = repo.find_by_email("nonexistent@example.com")
        assert user is None

    def test_find_by_email_is_case_insensitive(self, db, test_user):
        """Should find user regardless of email case."""
        repo = UserRepository(db)
        user = repo.find_by_email("TEST@EXAMPLE.COM")
        assert user is not None
        assert user.email == "test@example.com"

    def test_find_active_by_id_returns_active_user(self, db, test_user):
        """Should return user when ID exists and user is active."""
        repo = UserRepository(db)
        user = repo.find_active_by_id(test_user.id)
        assert user is not None
        assert user.id == test_user.id
        assert user.is_active is True

    def test_find_active_by_id_returns_none_for_inactive_user(self, db, test_user):
        """Should return None when user exists but is inactive."""
        test_user.is_active = False
        db.commit()

        repo = UserRepository(db)
        user = repo.find_active_by_id(test_user.id)
        assert user is None

    def test_find_verified_by_email_returns_verified_user(self, db, test_user):
        """Should return user when email exists, is active, and verified."""
        repo = UserRepository(db)
        user = repo.find_verified_by_email("test@example.com")
        assert user is not None
        assert user.email == "test@example.com"
        assert user.is_active is True
        assert user.email_verified is True

    def test_find_verified_by_email_returns_none_for_unverified(self, db, test_user):
        """Should return None when user is not email verified."""
        test_user.email_verified = False
        db.commit()

        repo = UserRepository(db)
        user = repo.find_verified_by_email("test@example.com")
        assert user is None

    def test_find_verified_by_email_returns_none_for_inactive(self, db, test_user):
        """Should return None when user is inactive."""
        test_user.is_active = False
        db.commit()

        repo = UserRepository(db)
        user = repo.find_verified_by_email("test@example.com")
        assert user is None

    def test_find_verified_by_email_is_case_insensitive(self, db, test_user):
        """Should find verified user regardless of email case."""
        repo = UserRepository(db)
        user = repo.find_verified_by_email("TEST@EXAMPLE.COM")
        assert user is not None
        assert user.email == "test@example.com"

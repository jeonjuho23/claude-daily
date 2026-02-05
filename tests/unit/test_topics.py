"""
Unit tests for config/topics.py
"""

import pytest

from config.topics import (
    CATEGORIES,
    TOPICS,
    get_all_topics,
    get_topics_by_category,
    get_category_name,
    get_total_topic_count,
    infer_category_from_topic,
)


class TestCategories:
    """Tests for CATEGORIES dictionary"""

    def test_categories_has_12_entries(self):
        """Verify 12 categories exist"""
        assert len(CATEGORIES) == 12

    def test_each_category_has_ko_and_en(self):
        """Each category should have Korean and English names"""
        for category, names in CATEGORIES.items():
            assert "ko" in names, f"{category} missing Korean name"
            assert "en" in names, f"{category} missing English name"


class TestTopics:
    """Tests for TOPICS dictionary"""

    def test_topics_matches_categories(self):
        """TOPICS keys should match CATEGORIES keys"""
        assert set(TOPICS.keys()) == set(CATEGORIES.keys())

    def test_each_category_has_topics(self):
        """Each category should have at least one topic"""
        for category, topics in TOPICS.items():
            assert len(topics) > 0, f"{category} has no topics"


class TestGetAllTopics:
    """Tests for get_all_topics function"""

    def test_returns_list_of_tuples(self):
        """Should return list of (category, topic) tuples"""
        all_topics = get_all_topics()
        assert isinstance(all_topics, list)
        assert all(isinstance(t, tuple) and len(t) == 2 for t in all_topics)

    def test_count_matches_total(self):
        """Number of topics should match get_total_topic_count"""
        all_topics = get_all_topics()
        assert len(all_topics) == get_total_topic_count()


class TestGetTopicsByCategory:
    """Tests for get_topics_by_category function"""

    def test_returns_topics_for_valid_category(self):
        """Should return topics list for valid category"""
        topics = get_topics_by_category("network")
        assert isinstance(topics, list)
        assert len(topics) > 0

    def test_returns_empty_for_invalid_category(self):
        """Should return empty list for invalid category"""
        topics = get_topics_by_category("invalid_category")
        assert topics == []


class TestGetCategoryName:
    """Tests for get_category_name function"""

    def test_returns_korean_name(self):
        """Should return Korean name by default"""
        name = get_category_name("network", "ko")
        assert name == "네트워크"

    def test_returns_english_name(self):
        """Should return English name when specified"""
        name = get_category_name("network", "en")
        assert name == "Network"

    def test_returns_category_key_for_invalid(self):
        """Should return category key for invalid category"""
        name = get_category_name("invalid", "ko")
        assert name == "invalid"


class TestGetTotalTopicCount:
    """Tests for get_total_topic_count function"""

    def test_returns_positive_count(self):
        """Should return a positive integer"""
        count = get_total_topic_count()
        assert isinstance(count, int)
        assert count > 0

    def test_matches_sum_of_all_categories(self):
        """Should match sum of topics in all categories"""
        expected = sum(len(topics) for topics in TOPICS.values())
        assert get_total_topic_count() == expected


class TestInferCategoryFromTopic:
    """Tests for infer_category_from_topic function"""

    def test_exact_match(self):
        """Should find category for exact topic match"""
        result = infer_category_from_topic("TCP vs UDP 비교")
        assert result == "network"

    def test_case_insensitive_match(self):
        """Should match regardless of case"""
        result = infer_category_from_topic("tcp vs udp 비교")
        assert result == "network"

    def test_partial_match(self):
        """Should find category with partial match"""
        result = infer_category_from_topic("TCP")
        assert result == "network"

    def test_returns_none_for_unknown(self):
        """Should return None for unknown topics"""
        result = infer_category_from_topic("completely unknown topic xyz123")
        assert result is None

    def test_strips_whitespace(self):
        """Should strip leading/trailing whitespace"""
        result = infer_category_from_topic("  TCP vs UDP 비교  ")
        assert result == "network"

    def test_algorithm_category(self):
        """Should correctly identify algorithm topics"""
        result = infer_category_from_topic("이진 탐색")
        assert result == "algorithm"

    def test_database_category(self):
        """Should correctly identify database topics"""
        result = infer_category_from_topic("트랜잭션 ACID 속성")
        assert result == "database"

    def test_design_pattern_category(self):
        """Should correctly identify design pattern topics"""
        result = infer_category_from_topic("싱글톤 패턴")
        assert result == "design_pattern"

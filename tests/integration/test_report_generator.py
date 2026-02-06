"""
Integration tests for src/reports/generator.py
"""

import pytest

from src.domain.enums import ReportType
from src.domain.models import ReportData
from src.reports.generator import ReportGenerator


@pytest.fixture
def report_gen(mock_repository, mock_slack_adapter, mock_notion_adapter):
    return ReportGenerator(
        repository=mock_repository,
        slack_adapter=mock_slack_adapter,
        notion_adapter=mock_notion_adapter,
    )


class TestWeeklyReport:
    @pytest.mark.asyncio
    async def test_generates_report_data(self, report_gen):
        report = await report_gen.generate_weekly_report()
        assert isinstance(report, ReportData)
        assert report.report_type == ReportType.WEEKLY.value

    @pytest.mark.asyncio
    async def test_creates_notion_page(self, report_gen, mock_notion_adapter):
        await report_gen.generate_weekly_report()
        mock_notion_adapter.create_report_page.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sends_slack_notification(self, report_gen, mock_slack_adapter):
        await report_gen.generate_weekly_report()
        mock_slack_adapter.send_report_notification.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handles_notion_failure(
        self, report_gen, mock_notion_adapter, mock_slack_adapter
    ):
        mock_notion_adapter.create_report_page.side_effect = Exception("Notion error")
        report = await report_gen.generate_weekly_report()
        # Should still send Slack notification without Notion URL
        assert isinstance(report, ReportData)
        mock_slack_adapter.send_report_notification.assert_awaited_once()
        # Check it was called without notion_url
        call_kwargs = mock_slack_adapter.send_report_notification.call_args
        # Second call (in except block) should have no notion_url
        assert call_kwargs.kwargs.get("notion_url") is None or len(call_kwargs.args) == 1

    @pytest.mark.asyncio
    async def test_success_rate_calculation(self, report_gen):
        report = await report_gen.generate_weekly_report()
        assert report.success_count == 9
        assert report.failed_count == 1

    @pytest.mark.asyncio
    async def test_duration_statistics(self, report_gen):
        report = await report_gen.generate_weekly_report()
        assert report.avg_duration_ms == 10500
        assert report.min_duration_ms == 8000
        assert report.max_duration_ms == 15000

    @pytest.mark.asyncio
    async def test_calculates_uncovered_categories(self, report_gen):
        report = await report_gen.generate_weekly_report()
        # mock returns {"network": 3, "os": 2}, so 10 categories uncovered
        assert len(report.uncovered_categories) == 10
        assert "network" not in report.uncovered_categories
        assert "os" not in report.uncovered_categories


class TestMonthlyReport:
    @pytest.mark.asyncio
    async def test_generates_monthly_data(self, report_gen):
        report = await report_gen.generate_monthly_report()
        assert isinstance(report, ReportData)
        assert report.report_type == ReportType.MONTHLY.value

    @pytest.mark.asyncio
    async def test_creates_notion_page(self, report_gen, mock_notion_adapter):
        await report_gen.generate_monthly_report()
        mock_notion_adapter.create_report_page.assert_awaited_once()


class TestReportData:
    @pytest.mark.asyncio
    async def test_handles_no_executions(
        self, mock_repository, mock_slack_adapter, mock_notion_adapter
    ):
        mock_repository.get_content_count.return_value = 0
        mock_repository.get_execution_stats.return_value = {}
        mock_repository.get_category_distribution.return_value = {}

        gen = ReportGenerator(
            repository=mock_repository,
            slack_adapter=mock_slack_adapter,
            notion_adapter=mock_notion_adapter,
        )
        report = await gen.generate_weekly_report()
        assert report.total_count == 0
        assert report.success_count == 0
        assert report.failed_count == 0
        assert report.avg_duration_ms is None


class TestReportsWithoutNotion:
    """Tests for report generation when Notion is not configured"""

    @pytest.fixture
    def report_gen_no_notion(self, mock_repository, mock_slack_adapter):
        return ReportGenerator(
            repository=mock_repository,
            slack_adapter=mock_slack_adapter,
            notion_adapter=None,
        )

    @pytest.mark.asyncio
    async def test_weekly_report_slack_only(self, report_gen_no_notion, mock_slack_adapter):
        """Weekly report should send Slack notification without Notion"""
        report = await report_gen_no_notion.generate_weekly_report()
        assert isinstance(report, ReportData)
        assert report.report_type == ReportType.WEEKLY.value
        mock_slack_adapter.send_report_notification.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_monthly_report_slack_only(self, report_gen_no_notion, mock_slack_adapter):
        """Monthly report should send Slack notification without Notion"""
        report = await report_gen_no_notion.generate_monthly_report()
        assert isinstance(report, ReportData)
        assert report.report_type == ReportType.MONTHLY.value
        mock_slack_adapter.send_report_notification.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_weekly_no_notion_url(self, report_gen_no_notion, mock_slack_adapter):
        """Slack notification should be sent without notion_url when Notion is None"""
        await report_gen_no_notion.generate_weekly_report()
        call_args = mock_slack_adapter.send_report_notification.call_args
        # Should be called with report only, no notion_url
        assert call_args.kwargs.get("notion_url") is None


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_execution_stats(
        self, mock_repository, mock_slack_adapter, mock_notion_adapter
    ):
        mock_repository.get_content_count.return_value = 0
        mock_repository.get_execution_stats.return_value = {
            "success": {
                "count": 0,
                "total_attempts": 0,
                "avg_duration_ms": None,
                "min_duration_ms": None,
                "max_duration_ms": None,
            },
            "failed": {
                "count": 0,
                "total_attempts": 0,
                "avg_duration_ms": None,
                "min_duration_ms": None,
                "max_duration_ms": None,
            },
        }
        mock_repository.get_category_distribution.return_value = {}

        gen = ReportGenerator(
            repository=mock_repository,
            slack_adapter=mock_slack_adapter,
            notion_adapter=mock_notion_adapter,
        )
        report = await gen.generate_weekly_report()
        assert report.total_count == 0
        assert report.success_count == 0
        assert report.failed_count == 0
        assert report.avg_duration_ms is None

    @pytest.mark.asyncio
    async def test_none_duration_fields(
        self, mock_repository, mock_slack_adapter, mock_notion_adapter
    ):
        mock_repository.get_content_count.return_value = 5
        mock_repository.get_execution_stats.return_value = {
            "success": {
                "count": 5,
                "total_attempts": 5,
                "avg_duration_ms": None,
                "min_duration_ms": None,
                "max_duration_ms": None,
            },
            "failed": {"count": 0, "total_attempts": 0},
        }
        mock_repository.get_category_distribution.return_value = {"network": 5}

        gen = ReportGenerator(
            repository=mock_repository,
            slack_adapter=mock_slack_adapter,
            notion_adapter=mock_notion_adapter,
        )
        report = await gen.generate_weekly_report()
        assert report.avg_duration_ms is None
        assert report.min_duration_ms is None
        assert report.max_duration_ms is None

    @pytest.mark.asyncio
    async def test_all_categories_uncovered(
        self, mock_repository, mock_slack_adapter, mock_notion_adapter
    ):
        mock_repository.get_content_count.return_value = 0
        mock_repository.get_execution_stats.return_value = {}
        mock_repository.get_category_distribution.return_value = {}

        gen = ReportGenerator(
            repository=mock_repository,
            slack_adapter=mock_slack_adapter,
            notion_adapter=mock_notion_adapter,
        )
        report = await gen.generate_weekly_report()
        assert len(report.uncovered_categories) == 12

    @pytest.mark.asyncio
    async def test_monthly_report_notion_failure(
        self, mock_repository, mock_slack_adapter, mock_notion_adapter
    ):
        mock_notion_adapter.create_report_page.side_effect = Exception("Notion error")
        gen = ReportGenerator(
            repository=mock_repository,
            slack_adapter=mock_slack_adapter,
            notion_adapter=mock_notion_adapter,
        )
        report = await gen.generate_monthly_report()
        assert isinstance(report, ReportData)
        # Slack notification should still be sent (fallback without notion_url)
        mock_slack_adapter.send_report_notification.assert_awaited()

    @pytest.mark.asyncio
    async def test_zero_retry_count(self, mock_repository, mock_slack_adapter, mock_notion_adapter):
        mock_repository.get_content_count.return_value = 5
        mock_repository.get_execution_stats.return_value = {
            "success": {
                "count": 5,
                "total_attempts": 5,
                "avg_duration_ms": 10000,
                "min_duration_ms": 8000,
                "max_duration_ms": 12000,
            },
            "failed": {"count": 0, "total_attempts": 0},
        }
        mock_repository.get_category_distribution.return_value = {"network": 5}

        gen = ReportGenerator(
            repository=mock_repository,
            slack_adapter=mock_slack_adapter,
            notion_adapter=mock_notion_adapter,
        )
        report = await gen.generate_weekly_report()
        assert report.retry_count == 0

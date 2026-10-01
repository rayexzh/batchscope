"""Pure snapshot selection and bilingual labels shared by the desktop review."""
import csv
import io

GROUP_FIELDS = {
    "01_test_ranges": ("product", "test_type", "method", "unit", "spec_low", "spec_high"),
    "02_deviation_backlog": ("product", "category"),
    "03_overdue_actions": ("action_id",),
}
REPORT_LABELS = {
    "01_test_ranges": "检验记录 / Measurements",
    "02_deviation_backlog": "偏差记录 / Deviations",
    "03_overdue_actions": "措施记录 / Actions",
}
STATUS_LABELS = {
    "due_today": "今天到期 / Due today",
    "due_soon": "1–7 天内到期 / Due in 1–7 days",
    "later": "7 天以后到期 / Due later",
    "not_opened": "尚未开启 / Not opened",
    "not_created": "尚未创建 / Not created",
    "completed": "已完成 / Completed",
    "not_due": "未逾期 / Not overdue",
    "outside_range": "超出示例范围 / Outside range",
    "within_range": "示例范围内 / Within range",
    "missing": "缺失结果 / Missing",
    "open": "未关闭 / Open",
    "closed": "已关闭 / Closed",
    "overdue": "逾期未完成 / Overdue",
}
FILTERS = {
    "01_test_ranges": ("outside_range", "missing", "within_range"),
    "02_deviation_backlog": ("open", "closed"),
    "03_overdue_actions": ("overdue",),
}
FIELD_LABELS = {
    "review_status": "复核状态 / Review status", "reviewer": "复核人 / Reviewer", "review_note": "复核备注 / Review note",
    "open_deviations": "未关闭偏差 / Open deviations", "overdue_actions": "逾期措施 / Overdue actions",
    "explanation": "说明 / Explanation",
    "date": "日期 / Date", "from_date": "起始日期 / From", "to_date": "截至日期 / To",
    "events": "累计事件 / Cumulative events", "flagged_events": "累计待复核事件 / Cumulative flagged events",
    "findings": "检查项 / Findings", "period_events": "本期事件 / Period events",
    "period_flagged_events": "本期待复核事件 / Period flagged events",
    "event_id": "事件编号 / Event ID", "rule": "检查规则 / Rule",
    "level": "提示类型 / Finding type", "source_row": "源记录行号 / Source row",
    "explanation_zh": "中文说明 / Chinese explanation",
    "explanation_en": "英文说明 / English explanation",
    "manufactured_on": "批次生产日期 / Manufactured",
    "parent_status": "关联偏差状态 / Parent deviation status",
    "days_until_due": "距到期天数（负值为逾期） / Days until due (negative = late)",
    "closed_parent_followup": "已关闭偏差需跟进（1=是） / Closed parent follow-up (1=yes)",
    "age_0_7": "积压 0–7 天 / Age 0–7 days", "age_8_30": "积压 8–30 天 / Age 8–30 days",
    "age_31_60": "积压 31–60 天 / Age 31–60 days", "age_61_plus": "积压 61 天以上 / Age 61+ days",
    "period": "月份 / Month", "period_end": "本期截止 / Period end",
    "opening_open": "期初积压 / Opening backlog", "opened_in_period": "本期开启 / Opened in period",
    "closed_in_period": "本期关闭 / Closed in period", "ending_open": "期末积压 / Ending backlog",
    "metric": "指标 / Metric", "before_value": "起始值 / Start value",
    "after_value": "截至值 / End value", "delta": "净变化 / Net change",
    "before_status": "起始状态 / Start status", "after_status": "截至状态 / End status",
    "change": "变化类型 / Movement", "before_overdue_days": "起始逾期天数 / Start days overdue",
    "after_overdue_days": "截至逾期天数 / End days overdue",
    "product": "产品 / Product", "test_type": "检验项目 / Test", "method": "方法 / Method",
    "unit": "单位 / Unit", "spec_low": "示例下限 / Low", "spec_high": "示例上限 / High",
    "measured_records": "检验记录数 / Records", "judgeable_records": "可判定数 / Judgeable",
    "missing_records": "缺失数 / Missing", "outside_range_records": "超范围数 / Outside",
    "outside_range_pct": "超范围比例 % / Rate", "category": "偏差类别 / Category",
    "opened_to_date": "累计开启数 / Opened", "open_records": "未关闭数 / Open",
    "oldest_open_days": "最长积压天数 / Oldest", "mean_open_age_days": "平均积压天数 / Mean age",
    "closed_records": "已关闭数 / Closed", "mean_closed_duration_days": "平均关闭天数 / Mean duration",
    "review_order": "复核顺序 / Order", "action_id": "措施编号 / Action",
    "deviation_id": "偏差编号 / Deviation", "owner_role": "负责人角色 / Role",
    "due_on": "到期日 / Due", "overdue_days": "逾期天数 / Days overdue",
    "test_id": "检验编号 / Test ID", "batch_id": "批次编号 / Batch", "value": "检验值 / Value",
    "measured_on": "检验日期 / Measured", "snapshot_status": "截至日期状态 / As-of status",
    "opened_on": "开启日期 / Opened", "closed_on_source": "源关闭日期 / Source closure",
    "open_age_days": "未关闭时长 / Open days", "closed_duration_days": "关闭耗时 / Duration",
    "created_on": "创建日期 / Created", "completed_on_source": "源完成日期 / Source completion",
}


def local_label(label, language=None):
    if language is None or " / " not in label:
        return label
    zh, en = label.split(" / ", 1)
    return en if language == "en" else zh


def field_label(field, language=None):
    return local_label(FIELD_LABELS.get(field, field), language)


def clipboard_row(columns, row, language=None):
    """TSV copy with field names, numeric negatives intact and formula-like text escaped."""
    values = []
    for field in columns:
        value = row[field]
        rendered = display_value(field, value, language)
        if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
            rendered = "'" + rendered
        values.append(rendered)
    handle = io.StringIO(newline="")
    writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
    writer.writerow([field_label(c, language) for c in columns])
    writer.writerow(values)
    return handle.getvalue().rstrip("\n")


def display_value(field, value, language=None):
    if value is None:
        return "—"
    if field == "review_status":
        from audit_notes import STATUSES
        label=STATUSES.get(value,(value,value))
        return label[1] if language=='en' else label[0] if language=='zh' else ' / '.join(label)
    if field in ("snapshot_status", "before_status", "after_status", "parent_status"):
        return local_label(STATUS_LABELS.get(value, value), language)
    if field in ("metric", "change"):
        from ui_text import TEXT, tr
        if value in TEXT:
            return tr(value, language) if language else tr(value, "zh") + " / " + tr(value, "en")
    if field == "delta" and isinstance(value, (int, float)) and value > 0:
        return "+" + str(value)
    return str(value)


def group_details(result, report, selected):
    """Use the stored snapshot, never mutable input files or a new GUI date value."""
    fields = GROUP_FIELDS[report]
    return [row for row in result["details"][report]
            if all(row[field] == selected[field] for field in fields)]


def filter_details(rows, status=None, search=""):
    needle = search.strip().casefold()
    return [row for row in rows
            if (status is None or row["snapshot_status"] == status)
            and (not needle or any(needle in display_value(key, value).casefold()
                                   for key, value in row.items()))]


def describe_group(report, selected, language=None):
    return " · ".join(f"{field_label(field, language)}: {display_value(field, selected[field], language)}"
                      for field in GROUP_FIELDS[report])

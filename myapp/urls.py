from django.urls import path

from . import (
    auth_views,
    dashboard_views,
    distribution_views,
    inventory_views,
    report_views,
    request_views,
)

urlpatterns = [
    # Authentication
    path("", auth_views.login_view, name="home"),
    path("login/", auth_views.login_view, name="login"),
    path("logout/", auth_views.logout_view, name="logout"),

    # Dashboard
    path("dashboard/", dashboard_views.dashboard_view, name="dashboard"),

    # Inventory, Shipments, Batches & Catalog
    path("inventory/", inventory_views.inventory_list_view, name="inventory_list"),
    path(
        "inventory/<int:inventory_id>/reorder/",
        inventory_views.update_reorder_level_view,
        name="update_reorder_level",
    ),
    path("shipments/receive/", inventory_views.receive_shipment_view, name="receive_shipment"),
    path("batches/", inventory_views.batch_list_view, name="batch_list"),
    path("commodities/", inventory_views.commodity_list_view, name="commodity_list"),
    path("commodities/create/", inventory_views.create_commodity_view, name="create_commodity"),

    # Branch Requests & Approvals
    path("requests/", request_views.request_list_view, name="requests_list"),
    path("requests/new/", request_views.create_request_view, name="create_request"),
    path(
        "requests/<int:request_id>/review/",
        request_views.review_request_view,
        name="review_request",
    ),

    # Stock Transfers & Deliveries
    path(
        "transfers-deliveries/",
        distribution_views.transfers_deliveries_view,
        name="transfers_deliveries",
    ),
    path(
        "transfers/dispatch/",
        distribution_views.dispatch_transfer_view,
        name="dispatch_transfer",
    ),
    path(
        "deliveries/<int:delivery_id>/confirm/",
        distribution_views.confirm_delivery_view,
        name="confirm_delivery",
    ),

    # Reports, Movements, Notifications & Audit Logs
    path("reports/", report_views.reports_analytics_view, name="reports_analytics"),
    path("movements/", report_views.stock_movements_view, name="stock_movements"),
    path("notifications/", report_views.notifications_view, name="notifications"),
    path(
        "notifications/<int:notification_id>/read/",
        report_views.mark_notification_read_view,
        name="mark_notification_read",
    ),
    path("audit-logs/", report_views.audit_logs_view, name="audit_logs"),

    # Administration (Facilities & Users)
    path("admin-mgmt/", dashboard_views.users_hospitals_view, name="users_hospitals"),
]
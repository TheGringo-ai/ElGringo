"""
Component Palette & Templates
=============================

Comprehensive UI components and app templates for the no-code builder.
50+ components across 8 categories.
"""

from typing import Dict, List, Any

# ============================================================
# COMPONENT PALETTE - 50+ Components
# ============================================================

COMPONENT_PALETTE = {
    "layout": {
        "display_name": "Layout",
        "icon": "grid",
        "components": [
            {"type": "container", "name": "Container", "icon": "square",
             "properties": {"padding": 16, "margin": 0, "direction": "column", "background": "transparent"},
             "description": "Flexible container for grouping elements"},
            {"type": "row", "name": "Row", "icon": "columns",
             "properties": {"gap": 16, "align": "center", "justify": "start", "wrap": True},
             "description": "Horizontal flex layout"},
            {"type": "column", "name": "Column", "icon": "rows",
             "properties": {"gap": 16, "width": "auto"},
             "description": "Vertical flex layout"},
            {"type": "grid", "name": "Grid", "icon": "grid",
             "properties": {"columns": 3, "gap": 16, "responsive": True},
             "description": "CSS Grid layout"},
            {"type": "card", "name": "Card", "icon": "credit-card",
             "properties": {"title": "", "subtitle": "", "shadow": "md", "padding": 24, "rounded": True},
             "description": "Card with optional header"},
            {"type": "section", "name": "Section", "icon": "layout",
             "properties": {"title": "", "background": "transparent", "fullWidth": False},
             "description": "Page section with optional title"},
            {"type": "modal", "name": "Modal", "icon": "square",
             "properties": {"title": "Modal", "size": "md", "closable": True},
             "description": "Popup dialog"},
            {"type": "drawer", "name": "Drawer", "icon": "sidebar",
             "properties": {"title": "", "position": "right", "size": 300},
             "description": "Slide-out panel"},
            {"type": "tabs", "name": "Tabs", "icon": "folder",
             "properties": {"tabs": ["Tab 1", "Tab 2", "Tab 3"], "variant": "default"},
             "description": "Tabbed content"},
            {"type": "accordion", "name": "Accordion", "icon": "chevrons-down",
             "properties": {"items": [{"title": "Section 1", "content": "Content..."}], "allowMultiple": False},
             "description": "Collapsible sections"},
            {"type": "divider", "name": "Divider", "icon": "minus",
             "properties": {"margin": 24, "color": "#e5e7eb"},
             "description": "Horizontal separator"},
            {"type": "spacer", "name": "Spacer", "icon": "maximize-2",
             "properties": {"height": 32},
             "description": "Vertical spacing"},
        ]
    },
    "input": {
        "display_name": "Forms",
        "icon": "edit-3",
        "components": [
            {"type": "text_field", "name": "Text Input", "icon": "type",
             "properties": {"label": "Label", "placeholder": "", "required": False, "helperText": ""},
             "data_type": "string", "description": "Single line text"},
            {"type": "email_field", "name": "Email", "icon": "mail",
             "properties": {"label": "Email", "placeholder": "you@example.com", "required": False},
             "data_type": "email", "description": "Email with validation"},
            {"type": "password_field", "name": "Password", "icon": "lock",
             "properties": {"label": "Password", "showToggle": True, "minLength": 8},
             "data_type": "password", "description": "Password input"},
            {"type": "number_field", "name": "Number", "icon": "hash",
             "properties": {"label": "Number", "min": None, "max": None, "step": 1},
             "data_type": "number", "description": "Numeric input"},
            {"type": "phone_field", "name": "Phone", "icon": "phone",
             "properties": {"label": "Phone", "placeholder": "+1 (555) 000-0000", "format": "US"},
             "data_type": "string", "description": "Phone with formatting"},
            {"type": "currency_field", "name": "Currency", "icon": "dollar-sign",
             "properties": {"label": "Amount", "currency": "USD", "min": 0},
             "data_type": "number", "description": "Money input"},
            {"type": "date_field", "name": "Date", "icon": "calendar",
             "properties": {"label": "Date", "format": "MM/DD/YYYY"},
             "data_type": "date", "description": "Date picker"},
            {"type": "time_field", "name": "Time", "icon": "clock",
             "properties": {"label": "Time", "format": "12h"},
             "data_type": "string", "description": "Time picker"},
            {"type": "datetime_field", "name": "Date & Time", "icon": "calendar",
             "properties": {"label": "Date & Time"},
             "data_type": "datetime", "description": "Combined picker"},
            {"type": "dropdown", "name": "Dropdown", "icon": "chevron-down",
             "properties": {"label": "Select", "options": ["Option 1", "Option 2"], "placeholder": "Choose...", "searchable": False},
             "data_type": "string", "description": "Select dropdown"},
            {"type": "multi_select", "name": "Multi Select", "icon": "check-square",
             "properties": {"label": "Select Multiple", "options": [], "max": None},
             "data_type": "array", "description": "Multiple selection"},
            {"type": "checkbox", "name": "Checkbox", "icon": "check-square",
             "properties": {"label": "I agree", "default": False},
             "data_type": "boolean", "description": "Single checkbox"},
            {"type": "checkbox_group", "name": "Checkbox Group", "icon": "check-square",
             "properties": {"label": "Options", "options": ["A", "B", "C"]},
             "data_type": "array", "description": "Multiple checkboxes"},
            {"type": "radio_group", "name": "Radio Group", "icon": "circle",
             "properties": {"label": "Choose One", "options": ["Option A", "Option B"]},
             "data_type": "string", "description": "Radio buttons"},
            {"type": "toggle", "name": "Toggle Switch", "icon": "toggle-left",
             "properties": {"label": "Enable", "default": False},
             "data_type": "boolean", "description": "On/off switch"},
            {"type": "textarea", "name": "Text Area", "icon": "align-left",
             "properties": {"label": "Message", "rows": 4, "placeholder": "", "maxLength": None},
             "data_type": "text", "description": "Multi-line text"},
            {"type": "rich_text", "name": "Rich Text Editor", "icon": "edit-2",
             "properties": {"label": "Content", "toolbar": ["bold", "italic", "link", "list"]},
             "data_type": "text", "description": "WYSIWYG editor"},
            {"type": "file_upload", "name": "File Upload", "icon": "upload",
             "properties": {"label": "Upload", "accept": "*", "multiple": False, "maxSize": "10MB"},
             "data_type": "file", "description": "File uploader"},
            {"type": "image_upload", "name": "Image Upload", "icon": "image",
             "properties": {"label": "Image", "accept": "image/*", "preview": True, "crop": False},
             "data_type": "file", "description": "Image with preview"},
            {"type": "slider", "name": "Slider", "icon": "sliders",
             "properties": {"label": "Value", "min": 0, "max": 100, "step": 1, "showValue": True},
             "data_type": "number", "description": "Range slider"},
            {"type": "rating", "name": "Rating", "icon": "star",
             "properties": {"label": "Rating", "max": 5, "allowHalf": False},
             "data_type": "number", "description": "Star rating"},
            {"type": "color_picker", "name": "Color Picker", "icon": "droplet",
             "properties": {"label": "Color", "default": "#3b82f6", "showHex": True},
             "data_type": "string", "description": "Color selector"},
        ]
    },
    "display": {
        "display_name": "Display",
        "icon": "eye",
        "components": [
            {"type": "heading", "name": "Heading", "icon": "type",
             "properties": {"text": "Heading", "level": 1, "align": "left"},
             "description": "H1-H6 heading"},
            {"type": "paragraph", "name": "Paragraph", "icon": "align-left",
             "properties": {"text": "Your text here...", "align": "left"},
             "description": "Text paragraph"},
            {"type": "text", "name": "Text", "icon": "type",
             "properties": {"content": "Text", "size": "md", "weight": "normal", "color": "inherit"},
             "description": "Inline text"},
            {"type": "image", "name": "Image", "icon": "image",
             "properties": {"src": "", "alt": "", "width": "100%", "rounded": False, "objectFit": "cover"},
             "description": "Display image"},
            {"type": "avatar", "name": "Avatar", "icon": "user",
             "properties": {"src": "", "name": "", "size": "md", "rounded": True},
             "description": "User avatar"},
            {"type": "icon", "name": "Icon", "icon": "star",
             "properties": {"name": "star", "size": 24, "color": "currentColor"},
             "description": "Display icon"},
            {"type": "badge", "name": "Badge", "icon": "tag",
             "properties": {"text": "New", "color": "primary", "variant": "solid"},
             "description": "Status badge"},
            {"type": "tag", "name": "Tag", "icon": "tag",
             "properties": {"text": "Tag", "color": "gray", "removable": False},
             "description": "Label tag"},
            {"type": "alert", "name": "Alert", "icon": "alert-circle",
             "properties": {"title": "", "message": "Alert message", "type": "info", "dismissible": True},
             "description": "Alert notification"},
            {"type": "tooltip", "name": "Tooltip", "icon": "help-circle",
             "properties": {"text": "Tooltip text", "position": "top"},
             "description": "Hover tooltip"},
            {"type": "progress", "name": "Progress Bar", "icon": "bar-chart",
             "properties": {"value": 50, "max": 100, "showLabel": True, "color": "primary"},
             "description": "Progress indicator"},
            {"type": "spinner", "name": "Loading Spinner", "icon": "loader",
             "properties": {"size": "md", "color": "primary"},
             "description": "Loading indicator"},
            {"type": "skeleton", "name": "Skeleton", "icon": "square",
             "properties": {"width": "100%", "height": 20, "rounded": True},
             "description": "Loading placeholder"},
            {"type": "empty_state", "name": "Empty State", "icon": "inbox",
             "properties": {"icon": "inbox", "title": "No data", "description": "Get started by creating something"},
             "description": "Empty content placeholder"},
            {"type": "stat_card", "name": "Stat Card", "icon": "trending-up",
             "properties": {"title": "Total Users", "value": "1,234", "change": "+12%", "changeType": "positive", "icon": "users"},
             "description": "Statistics display"},
            {"type": "countdown", "name": "Countdown", "icon": "clock",
             "properties": {"targetDate": "", "format": "DD:HH:MM:SS"},
             "description": "Countdown timer"},
            {"type": "code_block", "name": "Code Block", "icon": "code",
             "properties": {"code": "", "language": "javascript", "showLineNumbers": True},
             "description": "Syntax highlighted code"},
            {"type": "markdown", "name": "Markdown", "icon": "file-text",
             "properties": {"content": "# Markdown content"},
             "description": "Render markdown"},
        ]
    },
    "action": {
        "display_name": "Actions",
        "icon": "mouse-pointer",
        "components": [
            {"type": "button", "name": "Button", "icon": "square",
             "properties": {"label": "Button", "variant": "primary", "size": "md", "icon": "", "loading": False},
             "description": "Action button"},
            {"type": "button_group", "name": "Button Group", "icon": "columns",
             "properties": {"buttons": [{"label": "One"}, {"label": "Two"}], "variant": "outline"},
             "description": "Grouped buttons"},
            {"type": "icon_button", "name": "Icon Button", "icon": "circle",
             "properties": {"icon": "plus", "variant": "ghost", "size": "md", "tooltip": ""},
             "description": "Icon-only button"},
            {"type": "link", "name": "Link", "icon": "link",
             "properties": {"text": "Click here", "href": "", "target": "_self", "underline": True},
             "description": "Navigation link"},
            {"type": "dropdown_menu", "name": "Dropdown Menu", "icon": "more-vertical",
             "properties": {"trigger": "Click", "items": [{"label": "Option 1"}, {"label": "Option 2"}]},
             "description": "Action menu"},
            {"type": "fab", "name": "Floating Action", "icon": "plus",
             "properties": {"icon": "plus", "position": "bottom-right", "color": "primary"},
             "description": "Floating action button"},
        ]
    },
    "data": {
        "display_name": "Data",
        "icon": "database",
        "components": [
            {"type": "data_table", "name": "Data Table", "icon": "table",
             "properties": {"model": "", "columns": [], "actions": ["view", "edit", "delete"],
                          "pagination": True, "pageSize": 10, "search": True, "sort": True, "filter": True},
             "description": "Full-featured data table"},
            {"type": "simple_table", "name": "Simple Table", "icon": "grid",
             "properties": {"headers": ["Col 1", "Col 2"], "rows": []},
             "description": "Basic table"},
            {"type": "list_view", "name": "List View", "icon": "list",
             "properties": {"model": "", "template": "card", "emptyText": "No items"},
             "description": "Data as list"},
            {"type": "kanban", "name": "Kanban Board", "icon": "trello",
             "properties": {"columns": ["To Do", "In Progress", "Done"], "model": ""},
             "description": "Kanban task board"},
            {"type": "calendar", "name": "Calendar", "icon": "calendar",
             "properties": {"model": "", "view": "month", "editable": True},
             "description": "Event calendar"},
            {"type": "timeline", "name": "Timeline", "icon": "git-commit",
             "properties": {"items": [], "orientation": "vertical"},
             "description": "Activity timeline"},
            {"type": "tree_view", "name": "Tree View", "icon": "git-branch",
             "properties": {"data": [], "expandable": True, "selectable": True},
             "description": "Hierarchical tree"},
            {"type": "form", "name": "Form", "icon": "file-text",
             "properties": {"model": "", "fields": [], "submitLabel": "Submit", "layout": "vertical"},
             "description": "Auto-generated form"},
            {"type": "search_box", "name": "Search", "icon": "search",
             "properties": {"placeholder": "Search...", "model": "", "instant": True},
             "description": "Search input"},
            {"type": "filter_panel", "name": "Filter Panel", "icon": "filter",
             "properties": {"filters": [], "layout": "horizontal"},
             "description": "Data filters"},
            {"type": "pagination", "name": "Pagination", "icon": "chevrons-right",
             "properties": {"total": 100, "pageSize": 10, "showInfo": True},
             "description": "Page navigation"},
        ]
    },
    "charts": {
        "display_name": "Charts",
        "icon": "bar-chart-2",
        "components": [
            {"type": "bar_chart", "name": "Bar Chart", "icon": "bar-chart-2",
             "properties": {"data": [], "xField": "", "yField": "", "color": "primary", "horizontal": False},
             "description": "Vertical/horizontal bars"},
            {"type": "line_chart", "name": "Line Chart", "icon": "trending-up",
             "properties": {"data": [], "xField": "", "yField": "", "smooth": True, "area": False},
             "description": "Line/area chart"},
            {"type": "pie_chart", "name": "Pie Chart", "icon": "pie-chart",
             "properties": {"data": [], "labelField": "", "valueField": "", "donut": False},
             "description": "Pie/donut chart"},
            {"type": "area_chart", "name": "Area Chart", "icon": "activity",
             "properties": {"data": [], "xField": "", "yField": "", "stacked": False},
             "description": "Filled area chart"},
            {"type": "scatter_chart", "name": "Scatter Plot", "icon": "target",
             "properties": {"data": [], "xField": "", "yField": "", "sizeField": ""},
             "description": "Scatter/bubble chart"},
            {"type": "gauge", "name": "Gauge", "icon": "activity",
             "properties": {"value": 75, "max": 100, "label": "", "color": "primary"},
             "description": "Gauge meter"},
            {"type": "sparkline", "name": "Sparkline", "icon": "activity",
             "properties": {"data": [], "type": "line", "color": "primary"},
             "description": "Mini inline chart"},
        ]
    },
    "auth": {
        "display_name": "Auth",
        "icon": "shield",
        "components": [
            {"type": "login_form", "name": "Login Form", "icon": "log-in",
             "properties": {"redirectTo": "/dashboard", "showRemember": True, "showForgot": True, "showSocial": True},
             "description": "Complete login form"},
            {"type": "signup_form", "name": "Signup Form", "icon": "user-plus",
             "properties": {"fields": ["name", "email", "password"], "redirectTo": "/dashboard", "showTerms": True},
             "description": "Registration form"},
            {"type": "forgot_password", "name": "Forgot Password", "icon": "key",
             "properties": {"redirectTo": "/login"},
             "description": "Password reset request"},
            {"type": "reset_password", "name": "Reset Password", "icon": "lock",
             "properties": {"redirectTo": "/login", "minLength": 8},
             "description": "Set new password"},
            {"type": "profile_card", "name": "Profile Card", "icon": "user",
             "properties": {"showAvatar": True, "showEmail": True, "showRole": True, "editable": False},
             "description": "User profile display"},
            {"type": "profile_form", "name": "Profile Form", "icon": "user",
             "properties": {"fields": ["name", "email", "avatar", "bio"]},
             "description": "Edit profile form"},
            {"type": "logout_button", "name": "Logout", "icon": "log-out",
             "properties": {"redirectTo": "/login", "label": "Logout", "confirmMessage": ""},
             "description": "Logout button"},
            {"type": "user_menu", "name": "User Menu", "icon": "user",
             "properties": {"showAvatar": True, "items": ["Profile", "Settings", "Logout"]},
             "description": "User dropdown menu"},
            {"type": "auth_guard", "name": "Auth Guard", "icon": "shield",
             "properties": {"redirectTo": "/login", "roles": []},
             "description": "Protected content wrapper"},
        ]
    },
    "navigation": {
        "display_name": "Navigation",
        "icon": "menu",
        "components": [
            {"type": "navbar", "name": "Navbar", "icon": "menu",
             "properties": {"brand": "My App", "logo": "", "links": [], "sticky": True, "transparent": False},
             "description": "Top navigation bar"},
            {"type": "sidebar", "name": "Sidebar", "icon": "sidebar",
             "properties": {"links": [], "collapsible": True, "defaultCollapsed": False, "width": 240},
             "description": "Side navigation"},
            {"type": "bottom_nav", "name": "Bottom Nav", "icon": "navigation",
             "properties": {"items": [{"icon": "home", "label": "Home"}, {"icon": "search", "label": "Search"}]},
             "description": "Mobile bottom nav"},
            {"type": "breadcrumb", "name": "Breadcrumb", "icon": "chevron-right",
             "properties": {"items": [{"label": "Home", "href": "/"}], "separator": "/"},
             "description": "Breadcrumb trail"},
            {"type": "steps", "name": "Steps", "icon": "list",
             "properties": {"steps": ["Step 1", "Step 2", "Step 3"], "current": 0, "clickable": False},
             "description": "Step indicator"},
            {"type": "footer", "name": "Footer", "icon": "minus-square",
             "properties": {"copyright": "© 2024", "links": [], "columns": 4, "showSocial": True},
             "description": "Page footer"},
        ]
    },
}


# ============================================================
# FULL APP TEMPLATES - Complete Working Applications
# ============================================================

FULL_APP_TEMPLATES = {
    "saas_dashboard": {
        "name": "SaaS Dashboard",
        "description": "Complete admin dashboard with analytics, user management, and settings",
        "icon": "layout",
        "preview_image": "/templates/saas-dashboard.png",
        "pages": [
            {
                "name": "Dashboard",
                "route": "/dashboard",
                "requires_auth": True,
                "components": [
                    {"type": "sidebar", "properties": {"links": [
                        {"icon": "home", "label": "Dashboard", "href": "/dashboard"},
                        {"icon": "users", "label": "Users", "href": "/users"},
                        {"icon": "bar-chart", "label": "Analytics", "href": "/analytics"},
                        {"icon": "settings", "label": "Settings", "href": "/settings"},
                    ]}},
                    {"type": "row", "properties": {"gap": 24}, "children": [
                        {"type": "stat_card", "properties": {"title": "Total Users", "value": "12,345", "change": "+12%", "icon": "users"}},
                        {"type": "stat_card", "properties": {"title": "Revenue", "value": "$45,678", "change": "+8%", "icon": "dollar-sign"}},
                        {"type": "stat_card", "properties": {"title": "Active Now", "value": "573", "change": "+23%", "icon": "activity"}},
                        {"type": "stat_card", "properties": {"title": "Conversion", "value": "3.2%", "change": "-2%", "icon": "trending-up"}},
                    ]},
                    {"type": "row", "properties": {"gap": 24}, "children": [
                        {"type": "card", "properties": {"title": "Revenue Overview"}, "children": [
                            {"type": "line_chart", "properties": {"data": "revenue", "xField": "month", "yField": "amount"}}
                        ]},
                        {"type": "card", "properties": {"title": "Recent Activity"}, "children": [
                            {"type": "timeline", "properties": {"items": []}}
                        ]},
                    ]},
                ]
            },
            {
                "name": "Users",
                "route": "/users",
                "requires_auth": True,
                "components": [
                    {"type": "heading", "properties": {"text": "User Management", "level": 1}},
                    {"type": "row", "properties": {"justify": "space-between"}, "children": [
                        {"type": "search_box", "properties": {"placeholder": "Search users..."}},
                        {"type": "button", "properties": {"label": "Add User", "variant": "primary", "icon": "plus"}},
                    ]},
                    {"type": "data_table", "properties": {
                        "model": "users",
                        "columns": ["name", "email", "role", "status", "created_at"],
                        "actions": ["edit", "delete"]
                    }},
                ]
            },
            {
                "name": "Settings",
                "route": "/settings",
                "requires_auth": True,
                "components": [
                    {"type": "heading", "properties": {"text": "Settings", "level": 1}},
                    {"type": "tabs", "properties": {"tabs": ["Profile", "Security", "Notifications", "Billing"]}},
                    {"type": "card", "children": [
                        {"type": "profile_form", "properties": {"fields": ["name", "email", "avatar", "bio"]}}
                    ]},
                ]
            },
            {
                "name": "Login",
                "route": "/login",
                "requires_auth": False,
                "components": [
                    {"type": "container", "properties": {"maxWidth": 400, "center": True}, "children": [
                        {"type": "card", "properties": {"padding": 32}, "children": [
                            {"type": "heading", "properties": {"text": "Welcome Back", "level": 2, "align": "center"}},
                            {"type": "login_form", "properties": {"redirectTo": "/dashboard"}}
                        ]}
                    ]}
                ]
            },
        ],
        "data_models": [
            {"name": "users", "fields": [
                {"name": "name", "type": "string", "required": True},
                {"name": "email", "type": "email", "required": True, "unique": True},
                {"name": "role", "type": "string", "default": "user"},
                {"name": "status", "type": "string", "default": "active"},
                {"name": "avatar", "type": "string"},
            ]},
        ],
        "auth_enabled": True,
    },

    "ecommerce_store": {
        "name": "E-commerce Store",
        "description": "Online store with products, cart, checkout, and order management",
        "icon": "shopping-cart",
        "preview_image": "/templates/ecommerce.png",
        "pages": [
            {
                "name": "Home",
                "route": "/",
                "components": [
                    {"type": "navbar", "properties": {"brand": "Store", "links": [
                        {"label": "Products", "href": "/products"},
                        {"label": "Cart", "href": "/cart"},
                    ]}},
                    {"type": "section", "properties": {"background": "#f8fafc"}, "children": [
                        {"type": "heading", "properties": {"text": "Welcome to Our Store", "level": 1, "align": "center"}},
                        {"type": "paragraph", "properties": {"text": "Discover amazing products", "align": "center"}},
                        {"type": "button", "properties": {"label": "Shop Now", "variant": "primary"}},
                    ]},
                    {"type": "heading", "properties": {"text": "Featured Products", "level": 2}},
                    {"type": "grid", "properties": {"columns": 4, "gap": 24}, "children": [
                        {"type": "card", "properties": {"title": "Product 1"}},
                        {"type": "card", "properties": {"title": "Product 2"}},
                        {"type": "card", "properties": {"title": "Product 3"}},
                        {"type": "card", "properties": {"title": "Product 4"}},
                    ]},
                ]
            },
            {
                "name": "Products",
                "route": "/products",
                "components": [
                    {"type": "row", "children": [
                        {"type": "filter_panel", "properties": {"filters": ["category", "price", "rating"]}},
                        {"type": "column", "children": [
                            {"type": "search_box", "properties": {"placeholder": "Search products..."}},
                            {"type": "grid", "properties": {"columns": 3}, "children": [
                                {"type": "card", "properties": {"title": "Product"}},
                            ]},
                        ]},
                    ]},
                ]
            },
            {
                "name": "Cart",
                "route": "/cart",
                "components": [
                    {"type": "heading", "properties": {"text": "Shopping Cart", "level": 1}},
                    {"type": "simple_table", "properties": {"headers": ["Product", "Qty", "Price", "Total"]}},
                    {"type": "card", "properties": {"title": "Order Summary"}, "children": [
                        {"type": "button", "properties": {"label": "Proceed to Checkout", "variant": "primary", "fullWidth": True}},
                    ]},
                ]
            },
            {
                "name": "Checkout",
                "route": "/checkout",
                "requires_auth": True,
                "components": [
                    {"type": "steps", "properties": {"steps": ["Shipping", "Payment", "Review"], "current": 0}},
                    {"type": "form", "properties": {"model": "orders", "fields": [
                        {"name": "address", "type": "textarea"},
                        {"name": "city", "type": "text"},
                        {"name": "zip", "type": "text"},
                    ]}},
                ]
            },
        ],
        "data_models": [
            {"name": "products", "fields": [
                {"name": "name", "type": "string", "required": True},
                {"name": "description", "type": "text"},
                {"name": "price", "type": "number", "required": True},
                {"name": "image", "type": "string"},
                {"name": "category", "type": "string"},
                {"name": "stock", "type": "integer", "default": 0},
            ]},
            {"name": "orders", "fields": [
                {"name": "user_id", "type": "reference", "ref": "users"},
                {"name": "items", "type": "json"},
                {"name": "total", "type": "number"},
                {"name": "status", "type": "string", "default": "pending"},
                {"name": "address", "type": "text"},
            ]},
        ],
        "auth_enabled": True,
    },

    "task_manager": {
        "name": "Task Manager",
        "description": "Kanban-style task management with projects and teams",
        "icon": "check-square",
        "preview_image": "/templates/tasks.png",
        "pages": [
            {
                "name": "Board",
                "route": "/",
                "requires_auth": True,
                "components": [
                    {"type": "navbar", "properties": {"brand": "TaskFlow"}},
                    {"type": "row", "properties": {"justify": "space-between"}, "children": [
                        {"type": "heading", "properties": {"text": "Project Board", "level": 1}},
                        {"type": "button", "properties": {"label": "New Task", "variant": "primary", "icon": "plus"}},
                    ]},
                    {"type": "kanban", "properties": {
                        "columns": ["Backlog", "To Do", "In Progress", "Review", "Done"],
                        "model": "tasks"
                    }},
                ]
            },
            {
                "name": "List",
                "route": "/list",
                "requires_auth": True,
                "components": [
                    {"type": "data_table", "properties": {
                        "model": "tasks",
                        "columns": ["title", "status", "priority", "assignee", "due_date"],
                        "actions": ["edit", "delete"]
                    }},
                ]
            },
            {
                "name": "Calendar",
                "route": "/calendar",
                "requires_auth": True,
                "components": [
                    {"type": "calendar", "properties": {"model": "tasks", "view": "month"}},
                ]
            },
        ],
        "data_models": [
            {"name": "tasks", "fields": [
                {"name": "title", "type": "string", "required": True},
                {"name": "description", "type": "text"},
                {"name": "status", "type": "string", "default": "backlog"},
                {"name": "priority", "type": "string", "default": "medium"},
                {"name": "assignee", "type": "reference", "ref": "users"},
                {"name": "due_date", "type": "date"},
                {"name": "project_id", "type": "reference", "ref": "projects"},
            ]},
            {"name": "projects", "fields": [
                {"name": "name", "type": "string", "required": True},
                {"name": "description", "type": "text"},
                {"name": "color", "type": "string", "default": "#3b82f6"},
            ]},
        ],
        "auth_enabled": True,
    },

    "blog_cms": {
        "name": "Blog / CMS",
        "description": "Content management system with posts, categories, and comments",
        "icon": "file-text",
        "preview_image": "/templates/blog.png",
        "pages": [
            {
                "name": "Home",
                "route": "/",
                "components": [
                    {"type": "navbar", "properties": {"brand": "Blog", "links": [
                        {"label": "Home", "href": "/"},
                        {"label": "Categories", "href": "/categories"},
                        {"label": "About", "href": "/about"},
                    ]}},
                    {"type": "section", "children": [
                        {"type": "heading", "properties": {"text": "Latest Posts", "level": 1}},
                        {"type": "grid", "properties": {"columns": 3, "gap": 24}, "children": [
                            {"type": "card", "properties": {"title": "Post Title"}},
                        ]},
                    ]},
                ]
            },
            {
                "name": "Post",
                "route": "/post/:slug",
                "components": [
                    {"type": "heading", "properties": {"text": "Post Title", "level": 1}},
                    {"type": "row", "children": [
                        {"type": "avatar", "properties": {"size": "sm"}},
                        {"type": "text", "properties": {"content": "Author Name • Jan 1, 2024"}},
                    ]},
                    {"type": "markdown", "properties": {"content": "Post content..."}},
                    {"type": "divider"},
                    {"type": "heading", "properties": {"text": "Comments", "level": 3}},
                ]
            },
            {
                "name": "Admin",
                "route": "/admin",
                "requires_auth": True,
                "components": [
                    {"type": "sidebar", "properties": {"links": [
                        {"icon": "file-text", "label": "Posts", "href": "/admin/posts"},
                        {"icon": "folder", "label": "Categories", "href": "/admin/categories"},
                        {"icon": "message-square", "label": "Comments", "href": "/admin/comments"},
                    ]}},
                    {"type": "data_table", "properties": {"model": "posts", "columns": ["title", "status", "author", "created_at"]}},
                ]
            },
        ],
        "data_models": [
            {"name": "posts", "fields": [
                {"name": "title", "type": "string", "required": True},
                {"name": "slug", "type": "string", "required": True, "unique": True},
                {"name": "content", "type": "text", "required": True},
                {"name": "excerpt", "type": "text"},
                {"name": "cover_image", "type": "string"},
                {"name": "status", "type": "string", "default": "draft"},
                {"name": "author_id", "type": "reference", "ref": "users"},
                {"name": "category_id", "type": "reference", "ref": "categories"},
            ]},
            {"name": "categories", "fields": [
                {"name": "name", "type": "string", "required": True},
                {"name": "slug", "type": "string", "required": True, "unique": True},
                {"name": "description", "type": "text"},
            ]},
            {"name": "comments", "fields": [
                {"name": "content", "type": "text", "required": True},
                {"name": "post_id", "type": "reference", "ref": "posts"},
                {"name": "author_id", "type": "reference", "ref": "users"},
                {"name": "status", "type": "string", "default": "pending"},
            ]},
        ],
        "auth_enabled": True,
    },

    "landing_page": {
        "name": "Landing Page",
        "description": "Marketing landing page with hero, features, pricing, and CTA",
        "icon": "star",
        "preview_image": "/templates/landing.png",
        "pages": [
            {
                "name": "Home",
                "route": "/",
                "components": [
                    {"type": "navbar", "properties": {"brand": "Product", "transparent": True, "links": [
                        {"label": "Features", "href": "#features"},
                        {"label": "Pricing", "href": "#pricing"},
                        {"label": "Contact", "href": "#contact"},
                    ]}},
                    {"type": "section", "properties": {"background": "gradient", "fullHeight": True}, "children": [
                        {"type": "heading", "properties": {"text": "Build Something Amazing", "level": 1, "align": "center"}},
                        {"type": "paragraph", "properties": {"text": "The platform that helps you create faster", "align": "center"}},
                        {"type": "row", "properties": {"justify": "center", "gap": 16}, "children": [
                            {"type": "button", "properties": {"label": "Get Started", "variant": "primary", "size": "lg"}},
                            {"type": "button", "properties": {"label": "Learn More", "variant": "outline", "size": "lg"}},
                        ]},
                    ]},
                    {"type": "section", "properties": {"id": "features"}, "children": [
                        {"type": "heading", "properties": {"text": "Features", "level": 2, "align": "center"}},
                        {"type": "grid", "properties": {"columns": 3, "gap": 32}, "children": [
                            {"type": "card", "properties": {"title": "Fast", "icon": "zap"}},
                            {"type": "card", "properties": {"title": "Secure", "icon": "shield"}},
                            {"type": "card", "properties": {"title": "Scalable", "icon": "trending-up"}},
                        ]},
                    ]},
                    {"type": "section", "properties": {"id": "pricing", "background": "#f8fafc"}, "children": [
                        {"type": "heading", "properties": {"text": "Pricing", "level": 2, "align": "center"}},
                        {"type": "grid", "properties": {"columns": 3, "gap": 24}, "children": [
                            {"type": "card", "properties": {"title": "Free", "subtitle": "$0/mo"}},
                            {"type": "card", "properties": {"title": "Pro", "subtitle": "$29/mo"}},
                            {"type": "card", "properties": {"title": "Enterprise", "subtitle": "Custom"}},
                        ]},
                    ]},
                    {"type": "footer", "properties": {"copyright": "© 2024 Company"}},
                ]
            },
        ],
        "data_models": [],
        "auth_enabled": False,
    },

    "crm": {
        "name": "CRM",
        "description": "Customer relationship management with contacts, deals, and pipeline",
        "icon": "users",
        "preview_image": "/templates/crm.png",
        "pages": [
            {
                "name": "Dashboard",
                "route": "/",
                "requires_auth": True,
                "components": [
                    {"type": "sidebar", "properties": {"links": [
                        {"icon": "home", "label": "Dashboard", "href": "/"},
                        {"icon": "users", "label": "Contacts", "href": "/contacts"},
                        {"icon": "briefcase", "label": "Deals", "href": "/deals"},
                        {"icon": "activity", "label": "Pipeline", "href": "/pipeline"},
                    ]}},
                    {"type": "row", "properties": {"gap": 24}, "children": [
                        {"type": "stat_card", "properties": {"title": "Total Contacts", "value": "1,234", "icon": "users"}},
                        {"type": "stat_card", "properties": {"title": "Open Deals", "value": "56", "icon": "briefcase"}},
                        {"type": "stat_card", "properties": {"title": "Revenue", "value": "$234,567", "icon": "dollar-sign"}},
                        {"type": "stat_card", "properties": {"title": "Win Rate", "value": "68%", "icon": "trending-up"}},
                    ]},
                ]
            },
            {
                "name": "Contacts",
                "route": "/contacts",
                "requires_auth": True,
                "components": [
                    {"type": "data_table", "properties": {
                        "model": "contacts",
                        "columns": ["name", "email", "company", "status", "last_contact"],
                        "actions": ["view", "edit", "delete"]
                    }},
                ]
            },
            {
                "name": "Pipeline",
                "route": "/pipeline",
                "requires_auth": True,
                "components": [
                    {"type": "kanban", "properties": {
                        "columns": ["Lead", "Qualified", "Proposal", "Negotiation", "Won", "Lost"],
                        "model": "deals"
                    }},
                ]
            },
        ],
        "data_models": [
            {"name": "contacts", "fields": [
                {"name": "name", "type": "string", "required": True},
                {"name": "email", "type": "email", "required": True},
                {"name": "phone", "type": "string"},
                {"name": "company", "type": "string"},
                {"name": "status", "type": "string", "default": "lead"},
                {"name": "notes", "type": "text"},
            ]},
            {"name": "deals", "fields": [
                {"name": "title", "type": "string", "required": True},
                {"name": "value", "type": "number"},
                {"name": "stage", "type": "string", "default": "lead"},
                {"name": "contact_id", "type": "reference", "ref": "contacts"},
                {"name": "probability", "type": "number", "default": 0},
                {"name": "close_date", "type": "date"},
            ]},
        ],
        "auth_enabled": True,
    },
}


# ============================================================
# APP TYPE TEMPLATES (Quick start types)
# ============================================================

APP_TYPE_TEMPLATES = {
    "web_app": {
        "name": "Web Application",
        "description": "General purpose website",
        "icon": "globe",
        "default_pages": ["Home", "About", "Contact"],
    },
    "dashboard": {
        "name": "Admin Dashboard",
        "description": "Data management with analytics",
        "icon": "layout",
        "default_pages": ["Dashboard", "Users", "Settings"],
    },
    "ecommerce": {
        "name": "E-commerce",
        "description": "Online store",
        "icon": "shopping-cart",
        "default_pages": ["Home", "Products", "Cart", "Checkout"],
    },
    "blog": {
        "name": "Blog / CMS",
        "description": "Content management",
        "icon": "file-text",
        "default_pages": ["Home", "Blog", "Post", "Admin"],
    },
    "crud": {
        "name": "CRUD App",
        "description": "Data management",
        "icon": "database",
        "default_pages": ["List", "Create", "Edit"],
    },
    "landing": {
        "name": "Landing Page",
        "description": "Marketing page",
        "icon": "star",
        "default_pages": ["Home"],
    },
    "saas": {
        "name": "SaaS Platform",
        "description": "Software as a service",
        "icon": "cloud",
        "default_pages": ["Landing", "Dashboard", "Settings", "Billing"],
    },
}


# ============================================================
# COMPONENT TEMPLATES (Pre-built combinations)
# ============================================================

COMPONENT_TEMPLATES = {
    "contact_form": {
        "name": "Contact Form",
        "description": "Name, email, message form",
        "components": [
            {"type": "heading", "properties": {"text": "Contact Us", "level": 2}},
            {"type": "text_field", "properties": {"label": "Name", "required": True}, "data_binding": "name"},
            {"type": "email_field", "properties": {"label": "Email", "required": True}, "data_binding": "email"},
            {"type": "textarea", "properties": {"label": "Message", "rows": 4, "required": True}, "data_binding": "message"},
            {"type": "button", "properties": {"label": "Send Message", "variant": "primary", "type": "submit"}},
        ]
    },
    "pricing_table": {
        "name": "Pricing Table",
        "description": "3-tier pricing cards",
        "components": [
            {"type": "grid", "properties": {"columns": 3, "gap": 24}, "children": [
                {"type": "card", "properties": {"title": "Basic", "subtitle": "$9/mo"}, "children": [
                    {"type": "list_view", "properties": {"items": ["Feature 1", "Feature 2"]}},
                    {"type": "button", "properties": {"label": "Get Started", "variant": "outline", "fullWidth": True}},
                ]},
                {"type": "card", "properties": {"title": "Pro", "subtitle": "$29/mo", "highlighted": True}, "children": [
                    {"type": "badge", "properties": {"text": "Popular", "color": "primary"}},
                    {"type": "list_view", "properties": {"items": ["Everything in Basic", "Feature 3", "Feature 4"]}},
                    {"type": "button", "properties": {"label": "Get Started", "variant": "primary", "fullWidth": True}},
                ]},
                {"type": "card", "properties": {"title": "Enterprise", "subtitle": "Custom"}, "children": [
                    {"type": "list_view", "properties": {"items": ["Everything in Pro", "Feature 5", "Dedicated Support"]}},
                    {"type": "button", "properties": {"label": "Contact Us", "variant": "outline", "fullWidth": True}},
                ]},
            ]},
        ]
    },
    "hero_section": {
        "name": "Hero Section",
        "description": "Landing page hero",
        "components": [
            {"type": "section", "properties": {"background": "#f8fafc", "padding": 80}, "children": [
                {"type": "container", "properties": {"maxWidth": 800, "center": True}, "children": [
                    {"type": "heading", "properties": {"text": "Build Something Amazing", "level": 1, "align": "center"}},
                    {"type": "paragraph", "properties": {"text": "The platform that helps you create faster than ever before.", "align": "center"}},
                    {"type": "row", "properties": {"justify": "center", "gap": 16}, "children": [
                        {"type": "button", "properties": {"label": "Get Started", "variant": "primary", "size": "lg"}},
                        {"type": "button", "properties": {"label": "Learn More", "variant": "outline", "size": "lg"}},
                    ]},
                ]},
            ]},
        ]
    },
    "user_table": {
        "name": "User Management",
        "description": "Users table with actions",
        "components": [
            {"type": "row", "properties": {"justify": "space-between", "margin_bottom": 24}, "children": [
                {"type": "search_box", "properties": {"placeholder": "Search users..."}},
                {"type": "button", "properties": {"label": "Add User", "variant": "primary", "icon": "plus"}},
            ]},
            {"type": "data_table", "properties": {
                "model": "users",
                "columns": ["name", "email", "role", "status", "created_at"],
                "actions": ["edit", "delete"]
            }},
        ]
    },
    "stats_row": {
        "name": "Stats Row",
        "description": "4 stat cards in a row",
        "components": [
            {"type": "row", "properties": {"gap": 24}, "children": [
                {"type": "stat_card", "properties": {"title": "Total Users", "value": "12,345", "change": "+12%", "icon": "users"}},
                {"type": "stat_card", "properties": {"title": "Revenue", "value": "$45,678", "change": "+8%", "icon": "dollar-sign"}},
                {"type": "stat_card", "properties": {"title": "Orders", "value": "1,234", "change": "+23%", "icon": "shopping-cart"}},
                {"type": "stat_card", "properties": {"title": "Conversion", "value": "3.2%", "change": "-2%", "icon": "trending-up"}},
            ]},
        ]
    },
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_component_by_type(component_type: str) -> Dict[str, Any]:
    """Get component definition by type"""
    for category in COMPONENT_PALETTE.values():
        for comp in category["components"]:
            if comp["type"] == component_type:
                return comp
    return None


def get_all_component_types() -> List[str]:
    """Get list of all component types"""
    types = []
    for category in COMPONENT_PALETTE.values():
        for comp in category["components"]:
            types.append(comp["type"])
    return types


def get_components_by_category(category: str) -> List[Dict]:
    """Get all components in a category"""
    if category in COMPONENT_PALETTE:
        return COMPONENT_PALETTE[category]["components"]
    return []


def get_template_by_name(template_name: str) -> Dict[str, Any]:
    """Get component template by name"""
    return COMPONENT_TEMPLATES.get(template_name)


def get_app_template(app_type: str) -> Dict[str, Any]:
    """Get app type template"""
    return APP_TYPE_TEMPLATES.get(app_type)


def get_full_app_template(template_name: str) -> Dict[str, Any]:
    """Get full app template"""
    return FULL_APP_TEMPLATES.get(template_name)


def count_components() -> int:
    """Count total components in palette"""
    total = 0
    for category in COMPONENT_PALETTE.values():
        total += len(category["components"])
    return total

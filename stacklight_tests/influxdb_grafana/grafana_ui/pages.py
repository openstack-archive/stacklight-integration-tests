from selenium.webdriver.common import by
from selenium.webdriver.common import keys


from stacklight_tests.helpers.ui import base_pages


class DashboardPage(base_pages.PageObject):
    _submenu_controls_locator = (
        by.By.CLASS_NAME,
        "submenu-controls"
    )

    def __init__(self, driver, dashboard_name):
        super(DashboardPage, self).__init__(driver)
        self._page_title = "Grafana - {}".format(dashboard_name)

    def is_dashboards_page(self):
        return (self.is_the_current_page() and
                self._is_element_visible(*self._submenu_controls_locator))

    def get_back_to_home(self):
        self.go_to_previous_page()
        return MainPage(self.driver)


class MainPage(base_pages.PageObject):
    _main_menu_locator = (
        by.By.CLASS_NAME,
        "navbar-brand-btn"
    )

    class MainDropDownMenu(base_pages.DropDownMenu):
        _default_src_locator = (
            by.By.CLASS_NAME,
            "navbar-brand-btn"
        )
        _options_list_locator = (
            by.By.CLASS_NAME,
            "sidemenu"
        )
        _items_locator = (
            by.By.CLASS_NAME,
            "dropdown"
        )

    class DashboardDropDownMenu(base_pages.DropDownMenu):
        _default_src_locator = (
            by.By.CLASS_NAME,
            "icon-gf-dashboard"
        )
        _options_list_locator = (
            by.By.CLASS_NAME,
            "search-results-container"
        )
        _items_locator = (
            by.By.CLASS_NAME,
            "search-item-dash-db"
        )

    def __init__(self, driver):
        super(MainPage, self).__init__(driver)
        self._page_title = "Grafana - Home"

    def is_main_page(self):
        return (self.is_the_current_page() and
                self._is_element_visible(*self._main_menu_locator))

    @property
    def main_menu(self):
        return self.MainDropDownMenu(self.driver)

    @property
    def dashboard_menu(self):
        return self.DashboardDropDownMenu(self.driver)

    def open_dashboard(self, dashboard_name):
        dashboards_mapping = {dashboard.text.lower(): dashboard
                              for dashboard in self.dashboard_menu.items}
        dashboards_mapping[dashboard_name.lower()].click()
        dashboard_page = DashboardPage(self.driver, dashboard_name)
        dashboard_page.is_dashboards_page()
        return dashboard_page


class LoginPage(base_pages.PageObject):
    _login_username_field_locator = (by.By.NAME, "username")
    _login_password_field_locator = (by.By.NAME, "password")
    _login_submit_button_locator = (by.By.CLASS_NAME, "btn")

    def __init__(self, driver):
        super(LoginPage, self).__init__(driver)
        self._page_title = "Grafana"

    def is_login_page(self):
        return (self.is_the_current_page() and
                self._is_element_visible(*self._login_submit_button_locator))

    @property
    def username(self):
        return self._get_element(*self._login_username_field_locator)

    @property
    def password(self):
        return self._get_element(*self._login_password_field_locator)

    @property
    def login_button(self):
        return self._get_element(*self._login_submit_button_locator)

    def _click_on_login_button(self):
        self.login_button.click()

    def _press_enter_on_login_button(self):
        self.login_button.send_keys(keys.Keys.RETURN)

    def login(self, user, password):
        return self.login_with_mouse_click(user, password)

    def login_with_mouse_click(self, user, password):
        return self._do_login(user, password, self._click_on_login_button)

    def login_with_enter_key(self, user, password):
        return self._do_login(user, password,
                              self._press_enter_on_login_button)

    def _do_login(self, user, password, login_method):
        return self.login_as_user(user, password, login_method)

    def login_as_user(self, user, password, login_method):
        self._fill_field_element(user, self.username)
        self._fill_field_element(password, self.password)
        login_method()
        return MainPage(self.driver)

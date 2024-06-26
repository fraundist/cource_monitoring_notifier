"""Initer module."""
import logging
from dataclasses import dataclass

import init_helpers
from aiohttp import ClientSession
from async_tools import AsyncInitable, AsyncDeinitable
from init_helpers import init_logs
from sqlalchemy_tools.database_connector.database_connector import DatabaseConnector
from sqlalchemy_tools.database_connector.database_session_maker import DatabaseSessionMaker

from controller import Controller
from database_actualizer import DatabaseActualizer
from monitoring_systems.abstract_monitoring_system_controller import AbstractMonitoringSystemController
from monitoring_systems.zabbix_controller import ZabbixController
from notifiers.abstract_notifier_controller import AbstractNotifierController
from notifiers.telegram.telegram_bot import TelegramBot
from notifiers.telegram.telegram_controller import TelegramController
from notifiers.telegram.telegram_dispatcher import TelegramDispatcher
from notifiers.telegram.telegram_keyboard_creator import TelegramKeyboardCreator
from notifiers.telegram.telegram_renderer import TelegramRenderer
from outer_resources.database_gateway import DatabaseGateway
from outer_resources.zabbix_connector import ZabbixConnector

logger = logging.getLogger(__name__)


@dataclass
class Initer:
    """Init all project components."""

    @dataclass
    class Config:
        """config."""

        logging: init_helpers.LogsConfig
        database_connector: DatabaseConnector.Config
        zabbix_controller: ZabbixController.Config
        zabbix_connector: ZabbixConnector.Config
        database_actualizer: DatabaseActualizer.Config
        telegram_bot: TelegramBot.Config = None

    config: Config

    @dataclass
    class Context(AsyncInitable, AsyncDeinitable):
        """context."""

        session: ClientSession = None
        database_connector: DatabaseConnector = None
        database_gateway: DatabaseGateway = None
        database_session_maker: DatabaseSessionMaker = None
        database_actualizer: DatabaseActualizer = None
        zabbix_controller: ZabbixController = None
        monitoring_system_controller: AbstractMonitoringSystemController = None
        zabbix_connector: ZabbixConnector = None
        telegram_bot: TelegramBot = None
        telegram_dispatcher: TelegramDispatcher = None
        telegram_controller: TelegramController = None
        telegram_renderer: TelegramRenderer = None
        telegram_keyboard_creator: TelegramKeyboardCreator = None
        notifier_controller: AbstractNotifierController = None

        controller: Controller = None

        def __post_init__(self):
            """Post init."""
            AsyncInitable.__init__(self)
            AsyncDeinitable.__init__(self)

    context: Context

    def __init__(self) -> None:
        """init."""
        self.context = self.Context()
        self.config = init_helpers.parse_args(config_file=init_helpers.Arg.ini_file_to_dataclass(self.Config))
        init_logs(self.config.logging)
        logger.info(f"Config: {self.config}")

    async def __aenter__(self) -> Controller:
        """aenter."""
        self._init_database_components()
        self._init_zabbix_components()
        self._init_telegram_components()

        self.context.controller = Controller(self.context)

        self.context.monitoring_system_controller = self.context.zabbix_controller
        self.context.notifier_controller = self.context.telegram_controller
        await self.context.async_init()
        return self.context.controller

    def _init_database_components(self) -> None:
        """Init all working with database classes."""
        self.context.database_connector = DatabaseConnector(self.config.database_connector)
        self.context.database_session_maker = DatabaseSessionMaker(self.context)
        self.context.database_gateway = DatabaseGateway(self.context)
        self.context.database_actualizer = DatabaseActualizer(self.config.database_actualizer, self.context)

    def _init_zabbix_components(self) -> None:
        """Init all working with Zabbix classes."""
        self.context.zabbix_connector = ZabbixConnector(self.config.zabbix_connector, self.context)
        self.context.zabbix_controller = ZabbixController(self.config.zabbix_controller, self.context)

    def _init_telegram_components(self) -> None:
        """Init all working with telegram classes."""
        self.context.telegram_bot = TelegramBot(self.config.telegram_bot)
        self.context.telegram_dispatcher = TelegramDispatcher(self.context)
        self.context.telegram_controller = TelegramController(self.context)
        self.context.telegram_renderer = TelegramRenderer()
        self.context.telegram_keyboard_creator = TelegramKeyboardCreator(self.context)

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """aexit."""
        if self.context.session is not None:
            await self.context.session.close()
        await self.context.async_deinit()
        logger.info("----===== Deinit done ====----")

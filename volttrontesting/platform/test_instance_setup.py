import contextlib
import os
import shutil
import subprocess
import pytest
from configparser import ConfigParser
from volttron.platform import is_rabbitmq_available
from volttron.platform.instance_setup import _is_agent_installed
from volttron.utils import get_hostname
from volttron.platform.agent.utils import is_volttron_running
from volttrontesting.utils.platformwrapper import create_volttron_home
from volttrontesting.utils.utils import get_rand_port

HAS_RMQ = is_rabbitmq_available()
RMQ_TIMEOUT = 600

if HAS_RMQ:
    from volttrontesting.fixtures.rmq_test_setup import create_rmq_volttron_setup

'''
Example variables to be used during each of the tests, depending on the prompts that will be asked

message_bus = "zmq"
rmq_home = ""
domain_name = ""
new_root_ca = "Y"
ca_country = "US"
ca_state = "test-state"
ca_location = "test-location"
ca_organization = "test-org"
ca_org_unit = "test-org-unit"
default_rmq_values = "Y"
remove_rmq_conf = "Y"
vip_address = ""
vip_port = ""
is_web_enabled = "Y"
web_protocol = "https"
web_port = ""
gen_web_cert = "Y"
is_vc = "N"
vc_admin_name = "test"
vc_admin_password = "test"
is_vcp = "N"
instance_name = ""
vc_hostname = ""
vc_port = ""
install_historian = "N"
install_driver = "N"
install_fake_device = "N"
install_listener = "N"
agent_autostart = "N"
'''


@contextlib.contextmanager
def create_vcfg_vhome():
    debug_flag = os.environ.get('DEBUG', False)
    vhome = create_volttron_home()
    yield vhome
    if not debug_flag:
        shutil.rmtree(vhome, ignore_errors=True)


def test_should_remove_config_vhome(monkeypatch):
    monkeypatch.setenv("DEBUG", '')
    with create_vcfg_vhome() as vhome:
        assert os.path.isdir(vhome)
    assert not os.path.isdir(vhome)


def test_should_not_remove_config_vhome_when_debugging(monkeypatch):
    monkeypatch.setenv("DEBUG", 1)
    with create_vcfg_vhome() as vhome:
        assert os.path.isdir(vhome)
    assert os.path.isdir(vhome)
    shutil.rmtree(vhome, ignore_errors=True)
    assert not os.path.isdir(vhome)


def test_zmq_case_no_agents(monkeypatch):
    with create_vcfg_vhome() as vhome:
        monkeypatch.setenv("VOLTTRON_HOME", vhome)
        config_path = os.path.join(vhome, "config")
        
        message_bus = "zmq"
        ip = "127.0.0.15"
        vip_address = "tcp://" + ip
        vip_port = str(get_rand_port(ip))
        instance_name = "test_zmq"
        is_web_enabled = "N"
        is_vcp = "N"
        install_historian = "N"
        install_driver = "N"
        install_listener = "N"

        vcfg_args = "\n".join([message_bus,
                               vip_address,
                               vip_port,
                               instance_name,
                               is_web_enabled,
                               is_vcp,
                               install_historian,
                               install_driver,
                               install_listener
                               ])

        with subprocess.Popen(["vcfg", "--vhome", vhome],
                              env=os.environ,
                              cwd=os.environ.get("VOLTTRON_ROOT"),
                              stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              text=True
                              ) as vcfg:
            out, err = vcfg.communicate(vcfg_args)
        #print("CWD is: {}".format(os.getcwd()))
        #print("OUT is: {}".format(out))
        #print("ERROR is: {}".format(err))
        assert os.path.exists(config_path)
        config = ConfigParser()
        config.read(config_path)
        assert config.get('volttron', 'message-bus') == "zmq"
        assert config.get('volttron', 'vip-address') == vip_address + ":" + vip_port
        assert config.get('volttron', 'instance-name').strip('"') == "test_zmq"
        assert not _is_agent_installed("listener")
        assert not _is_agent_installed("platform_driver")
        assert not _is_agent_installed("platform_historian")
        assert not _is_agent_installed("vc ")
        assert not _is_agent_installed("vcp")
        assert not is_volttron_running(vhome)


@pytest.mark.timeout(400)
def test_zmq_case_with_agents(monkeypatch):
    with create_vcfg_vhome() as vhome:
        monkeypatch.setenv("VOLTTRON_HOME", vhome)
        config_path = os.path.join(vhome, "config")

        message_bus = "zmq"
        ip = '127.0.0.15'
        vip_address = "tcp://" + ip
        vip_port = str(get_rand_port(ip))
        is_web_enabled = "N"
        is_vcp = "Y"
        instance_name = "test_zmq"
        vc_hostname = "{}{}".format("https://", get_hostname())
        vc_port = str(get_rand_port(ip))
        install_historian = "Y"
        install_driver = "Y"
        install_fake_device = "Y"
        install_listener = "Y"
        agent_autostart = "N"

        vcfg_args = "\n".join([message_bus,
                               vip_address,
                               vip_port,
                               instance_name,
                               is_web_enabled,
                               is_vcp,
                               vc_hostname,
                               vc_port,
                               agent_autostart,
                               install_historian,
                               agent_autostart,
                               install_driver,
                               install_fake_device,
                               agent_autostart,
                               install_listener,
                               agent_autostart
                               ])

        with subprocess.Popen(["vcfg", "--vhome", vhome],
                              env=os.environ,
                              cwd=os.environ.get("VOLTTRON_ROOT"),
                              stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              text=True
                              ) as vcfg:
            out, err = vcfg.communicate(vcfg_args)

        assert os.path.exists(config_path)
        config = ConfigParser()
        config.read(config_path)
        assert config.get('volttron', 'message-bus') == "zmq"
        assert config.get('volttron', 'vip-address') == vip_address + ":" + vip_port
        assert config.get('volttron', 'instance-name').strip('"') == "test_zmq"
        assert _is_agent_installed("listener")
        assert _is_agent_installed("platform_driver")
        assert _is_agent_installed("platform_historian")
        assert _is_agent_installed("vcp")
        assert not _is_agent_installed("vc ")

        assert not is_volttron_running(vhome)


def test_zmq_case_web_no_agents(monkeypatch):
    with create_vcfg_vhome() as vhome:
        monkeypatch.setenv("VOLTTRON_HOME", vhome)
        config_path = os.path.join(vhome, "config")

        message_bus = "zmq"
        ip = '127.0.0.15'
        vip_address = "tcp://" + ip
        vip_port = str(get_rand_port(ip))
        instance_name = "test_zmq"
        is_web_enabled = "Y"
        web_protocol = "https"
        web_port = str(get_rand_port(ip, 8000, 9000))
        gen_web_cert = "Y"
        new_root_ca = "Y"
        ca_country = "US"
        ca_state = "test-state"
        ca_location = "test-location"
        ca_organization = "test-org"
        ca_org_unit = "test-org-unit"
        is_vc = "N"
        is_vcp = "N"
        install_historian = "N"
        install_driver = "N"
        install_listener = "N"

        vcfg_args = "\n".join([message_bus,
                               vip_address,
                               vip_port,
                               instance_name,
                               is_web_enabled,
                               web_protocol,
                               web_port,
                               gen_web_cert,
                               new_root_ca,
                               ca_country,
                               ca_state,
                               ca_location,
                               ca_organization,
                               ca_org_unit,
                               is_vc,
                               is_vcp,
                               install_historian,
                               install_driver,
                               install_listener
                               ])

        with subprocess.Popen(["vcfg", "--vhome", vhome],
                              env=os.environ,
                              cwd=os.environ.get("VOLTTRON_ROOT"),
                              stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              text=True
                              ) as vcfg:
            out, err = vcfg.communicate(vcfg_args)

        assert os.path.exists(config_path)
        config = ConfigParser()
        config.read(config_path)
        assert config.get('volttron', 'message-bus') == "zmq"
        assert config.get('volttron', 'vip-address') == vip_address + ":" + vip_port
        assert config.get('volttron', 'instance-name').strip('"') == "test_zmq"
        assert config.get('volttron', 'bind-web-address') ==\
               "{}{}:{}".format("https://", get_hostname().lower(), web_port)
        assert config.get('volttron', 'web-ssl-cert') == \
               os.path.join(vhome, "certificates", "certs", "platform_web-server.crt")
        assert config.get('volttron', 'web-ssl-key') == \
               os.path.join(vhome, "certificates", "private", "platform_web-server.pem")
        assert not _is_agent_installed("listener")
        assert not _is_agent_installed("platform_driver")
        assert not _is_agent_installed("platform_historian")
        assert not _is_agent_installed("vc ")
        assert not _is_agent_installed("vcp")
        assert not is_volttron_running(vhome)


@pytest.mark.timeout(400)
def test_zmq_case_web_with_agents(monkeypatch):
    with create_vcfg_vhome() as vhome:
        monkeypatch.setenv("VOLTTRON_HOME", vhome)
        config_path = os.path.join(vhome, "config")

        message_bus = "zmq"
        ip = '127.0.0.15'
        vip_address = "tcp://" + ip
        vip_port = str(get_rand_port(ip))
        instance_name = "test_zmq"
        is_web_enabled = "Y"
        web_protocol = "https"
        web_port = str(get_rand_port(ip, 8000, 9000))
        gen_web_cert = "Y"
        new_root_ca = "Y"
        ca_country = "US"
        ca_state = "test-state"
        ca_location = "test-location"
        ca_organization = "test-org"
        ca_org_unit = "test-org-unit"
        is_vc = "N"
        is_vcp = "Y"
        vc_hostname = "{}{}".format("https://", get_hostname())
        vc_port = str(get_rand_port(ip))
        install_historian = "Y"
        install_driver = "Y"
        install_fake_device = "Y"
        install_listener = "Y"
        agent_autostart = "N"
        vcfg_args = "\n".join([message_bus,
                               vip_address,
                               vip_port,
                               instance_name,
                               is_web_enabled,
                               web_protocol,
                               web_port,
                               gen_web_cert,
                               new_root_ca,
                               ca_country,
                               ca_state,
                               ca_location,
                               ca_organization,
                               ca_org_unit,
                               is_vc,
                               is_vcp,
                               vc_hostname,
                               vc_port,
                               agent_autostart,
                               install_historian,
                               agent_autostart,
                               install_driver,
                               install_fake_device,
                               agent_autostart,
                               install_listener,
                               agent_autostart
                               ])

        with subprocess.Popen(["vcfg", "--vhome", vhome],
                              env=os.environ,
                              cwd=os.environ.get("VOLTTRON_ROOT"),
                              stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              text=True
                              ) as vcfg:
            out, err = vcfg.communicate(vcfg_args)

        assert os.path.exists(config_path)
        config = ConfigParser()
        config.read(config_path)
        assert config.get('volttron', 'message-bus') == "zmq"
        assert config.get('volttron', 'vip-address') == vip_address + ":" + vip_port
        assert config.get('volttron', 'instance-name').strip('"') == "test_zmq"
        assert config.get('volttron', 'bind-web-address') == \
               "{}{}:{}".format("https://", get_hostname().lower(), web_port)
        assert config.get('volttron', 'web-ssl-cert') == \
               os.path.join(vhome, "certificates", "certs", "platform_web-server.crt")
        assert config.get('volttron', 'web-ssl-key') == \
               os.path.join(vhome, "certificates", "private", "platform_web-server.pem")
        assert _is_agent_installed("listener")
        assert _is_agent_installed("platform_driver")
        assert _is_agent_installed("platform_historian")
        assert not _is_agent_installed("vc ")
        assert _is_agent_installed("vcp")
        assert not is_volttron_running(vhome)


def test_zmq_case_web_vc(monkeypatch):
    with create_vcfg_vhome() as vhome:
        monkeypatch.setenv("VOLTTRON_HOME", vhome)
        config_path = os.path.join(vhome, "config")

        message_bus = "zmq"
        ip = '127.0.0.15'
        vip_address = "tcp://" + ip
        vip_port = str(get_rand_port(ip))
        instance_name = "test_zmq"
        is_web_enabled = "Y"
        web_protocol = "https"
        web_port = str(get_rand_port(ip, 8000, 9000))
        gen_web_cert = "Y"
        new_root_ca = "Y"
        ca_country = "US"
        ca_state = "test-state"
        ca_location = "test-location"
        ca_organization = "test-org"
        ca_org_unit = "test-org-unit"
        is_vc = "Y"
        is_vcp = "Y"
        install_historian = "N"
        install_driver = "N"
        install_listener = "N"
        agent_autostart = "N"
        vcfg_args = "\n".join([message_bus,
                               vip_address,
                               vip_port,
                               instance_name,
                               is_web_enabled,
                               web_protocol,
                               web_port,
                               gen_web_cert,
                               new_root_ca,
                               ca_country,
                               ca_state,
                               ca_location,
                               ca_organization,
                               ca_org_unit,
                               is_vc,
                               agent_autostart,
                               is_vcp,
                               agent_autostart,
                               install_historian,
                               install_driver,
                               install_listener
                               ])

        with subprocess.Popen(["vcfg", "--vhome", vhome],
                              env=os.environ,
                              cwd=os.environ.get("VOLTTRON_ROOT"),
                              stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              text=True
                              ) as vcfg:
            out, err = vcfg.communicate(vcfg_args)

        assert os.path.exists(config_path)
        config = ConfigParser()
        config.read(config_path)
        assert config.get('volttron', 'message-bus') == "zmq"
        assert config.get('volttron', 'vip-address') == vip_address + ":" + vip_port
        assert config.get('volttron', 'instance-name').strip('"') == "test_zmq"
        assert config.get('volttron', 'volttron-central-address') == \
               "{}{}:{}".format("https://", get_hostname().lower(), web_port)
        assert config.get('volttron', 'bind-web-address') == \
               "{}{}:{}".format("https://", get_hostname().lower(), web_port)
        assert config.get('volttron', 'web-ssl-cert') == \
               os.path.join(vhome, "certificates", "certs", "platform_web-server.crt")
        assert config.get('volttron', 'web-ssl-key') == \
               os.path.join(vhome, "certificates", "private", "platform_web-server.pem")
        assert not _is_agent_installed("listener")
        assert not _is_agent_installed("platform_driver")
        assert not _is_agent_installed("platform_historian")
        assert _is_agent_installed("vc ")
        assert _is_agent_installed("vcp")
        assert not is_volttron_running(vhome)


def test_zmq_case_web_vc_with_agents(monkeypatch):
    with create_vcfg_vhome() as vhome:
        monkeypatch.setenv("VOLTTRON_HOME", vhome)
        config_path = os.path.join(vhome, "config")

        message_bus = "zmq"
        ip = '127.0.0.15'
        vip_address = "tcp://" + ip
        vip_port = str(get_rand_port(ip))
        instance_name = "test_zmq"
        is_web_enabled = "Y"
        web_protocol = "https"
        web_port = str(get_rand_port(ip, 8000, 9000))
        gen_web_cert = "Y"
        new_root_ca = "Y"
        ca_country = "US"
        ca_state = "test-state"
        ca_location = "test-location"
        ca_organization = "test-org"
        ca_org_unit = "test-org-unit"
        is_vc = "Y"
        is_vcp = "Y"
        install_historian = "Y"
        install_driver = "Y"
        install_fake_device = "Y"
        install_listener = "Y"
        agent_autostart = "N"
        vcfg_args = "\n".join([message_bus,
                               vip_address,
                               vip_port,
                               instance_name,
                               is_web_enabled,
                               web_protocol,
                               web_port,
                               gen_web_cert,
                               new_root_ca,
                               ca_country,
                               ca_state,
                               ca_location,
                               ca_organization,
                               ca_org_unit,
                               is_vc,
                               agent_autostart,
                               is_vcp,
                               agent_autostart,
                               install_historian,
                               agent_autostart,
                               install_driver,
                               install_fake_device,
                               agent_autostart,
                               install_listener,
                               agent_autostart
                               ])

        with subprocess.Popen(["vcfg", "--vhome", vhome],
                              env=os.environ,
                              cwd=os.environ.get("VOLTTRON_ROOT"),
                              stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              text=True
                              ) as vcfg:
            out, err = vcfg.communicate(vcfg_args)

        assert os.path.exists(config_path)
        config = ConfigParser()
        config.read(config_path)
        assert config.get('volttron', 'message-bus') == "zmq"
        assert config.get('volttron', 'vip-address') == vip_address + ":" + vip_port
        assert config.get('volttron', 'instance-name').strip('"') == "test_zmq"
        assert config.get('volttron', 'volttron-central-address') == \
               "{}{}:{}".format("https://", get_hostname().lower(), web_port)
        assert config.get('volttron', 'bind-web-address') == \
               "{}{}:{}".format("https://", get_hostname().lower(), web_port)
        assert config.get('volttron', 'web-ssl-cert') == \
               os.path.join(vhome, "certificates", "certs", "platform_web-server.crt")
        assert config.get('volttron', 'web-ssl-key') == \
               os.path.join(vhome, "certificates", "private", "platform_web-server.pem")
        assert _is_agent_installed("listener")
        assert _is_agent_installed("platform_driver")
        assert _is_agent_installed("platform_historian")
        assert _is_agent_installed("vc ")
        assert _is_agent_installed("vcp")
        assert not is_volttron_running(vhome)


@pytest.mark.skipif(not HAS_RMQ, reason='RabbitMQ is not setup')
@pytest.mark.timeout(RMQ_TIMEOUT)
def test_rmq_case_no_agents(monkeypatch):
    with create_vcfg_vhome() as vhome:
        monkeypatch.setenv("VOLTTRON_HOME", vhome)
        monkeypatch.setenv("RABBITMQ_CONF_ENV_FILE", "")
        config_path = os.path.join(vhome, "config")

        message_bus = "rmq"
        instance_name = "test_rmq"
        ip = '127.0.0.15'
        vip_address = "tcp://" + ip
        vip_port = str(get_rand_port(ip))
        is_web_enabled = "N"
        is_vcp = "N"
        install_historian = "N"
        install_driver = "N"
        install_listener = "N"

        create_rmq_volttron_setup(vhome=vhome, env=os.environ, ssl_auth=True, instance_name=instance_name)

        vcfg_args = "\n".join([message_bus,
                               vip_address,
                               vip_port,
                               instance_name,
                               is_web_enabled,
                               is_vcp,
                               install_historian,
                               install_driver,
                               install_listener
                               ])

        with subprocess.Popen(["vcfg", "--vhome", vhome],
                              env=os.environ,
                              cwd=os.environ.get("VOLTTRON_ROOT"),
                              stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              text=True
                              ) as vcfg:
            out, err = vcfg.communicate(vcfg_args)

        assert os.path.exists(config_path)
        config = ConfigParser()
        config.read(config_path)
        assert config.get('volttron', 'message-bus') == "rmq"
        assert config.get('volttron', 'vip-address') == vip_address + ":" + vip_port
        assert config.get('volttron', 'instance-name').strip('"') == "test_rmq"
        assert not _is_agent_installed("listener")
        assert not _is_agent_installed("platform_driver")
        assert not _is_agent_installed("platform_historian")
        assert not _is_agent_installed("vc ")
        assert not _is_agent_installed("vcp")
        assert not is_volttron_running(vhome)


@pytest.mark.skipif(not HAS_RMQ, reason='RabbitMQ is not setup')
@pytest.mark.timeout(RMQ_TIMEOUT)
def test_rmq_case_with_agents(monkeypatch):
    with create_vcfg_vhome() as vhome:
        monkeypatch.setenv("VOLTTRON_HOME", vhome)
        monkeypatch.setenv("RABBITMQ_CONF_ENV_FILE", "")
        config_path = os.path.join(vhome, "config")

        message_bus = "rmq"
        instance_name = "test_rmq"
        ip = '127.0.0.15'
        vip_address = "tcp://" + ip
        vip_port = str(get_rand_port(ip))
        is_web_enabled = "N"
        is_vcp = "Y"
        vc_hostname = "{}{}".format("https://", get_hostname())
        vc_port = str(get_rand_port(ip))
        install_historian = "Y"
        install_driver = "Y"
        install_fake_device = "Y"
        install_listener = "Y"
        agent_autostart = "N"

        create_rmq_volttron_setup(vhome=vhome, env=os.environ, ssl_auth=True, instance_name=instance_name)

        vcfg_args = "\n".join([message_bus,
                               vip_address,
                               vip_port,
                               instance_name,
                               is_web_enabled,
                               is_vcp,
                               vc_hostname,
                               vc_port,
                               agent_autostart,
                               install_historian,
                               agent_autostart,
                               install_driver,
                               install_fake_device,
                               agent_autostart,
                               install_listener,
                               agent_autostart
                               ])

        with subprocess.Popen(["vcfg", "--vhome", vhome],
                              env=os.environ,
                              cwd=os.environ.get("VOLTTRON_ROOT"),
                              stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              text=True
                              ) as vcfg:
            out, err = vcfg.communicate(vcfg_args)

        assert os.path.exists(config_path)
        config = ConfigParser()
        config.read(config_path)
        assert config.get('volttron', 'message-bus') == "rmq"
        assert config.get('volttron', 'vip-address') == vip_address + ":" + vip_port
        assert config.get('volttron', 'instance-name').strip('"') == "test_rmq"
        assert _is_agent_installed("listener")
        assert _is_agent_installed("platform_driver")
        assert _is_agent_installed("platform_historian")
        assert _is_agent_installed("vcp")
        assert not _is_agent_installed("vc ")

        assert not is_volttron_running(vhome)


@pytest.mark.skipif(not HAS_RMQ, reason='RabbitMQ is not setup')
@pytest.mark.timeout(RMQ_TIMEOUT)
def test_rmq_case_web_no_agents(monkeypatch):
    with create_vcfg_vhome() as vhome:
        monkeypatch.setenv("VOLTTRON_HOME", vhome)
        monkeypatch.setenv("RABBITMQ_CONF_ENV_FILE", "")
        config_path = os.path.join(vhome, "config")

        message_bus = "rmq"
        instance_name = "test_rmq"
        is_web_enabled = "Y"
        is_vc = "N"
        is_vcp = "N"
        ip = '127.0.0.15'
        web_port = str(get_rand_port(ip, 8000, 9000))
        vip_address = "tcp://" + ip
        vip_port = str(get_rand_port(ip))
        install_historian = "N"
        install_driver = "N"
        install_listener = "N"

        create_rmq_volttron_setup(vhome=vhome, env=os.environ, ssl_auth=True, instance_name=instance_name)

        vcfg_args = "\n".join([message_bus,
                               vip_address,
                               vip_port,
                               instance_name,
                               is_web_enabled,
                               web_port,
                               is_vc,
                               is_vcp,
                               install_historian,
                               install_driver,
                               install_listener
                               ])

        with subprocess.Popen(["vcfg", "--vhome", vhome],
                              env=os.environ,
                              cwd=os.environ.get("VOLTTRON_ROOT"),
                              stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              text=True
                              ) as vcfg:
            out, err = vcfg.communicate(vcfg_args)

        assert os.path.exists(config_path)
        config = ConfigParser()
        config.read(config_path)
        assert config.get('volttron', 'message-bus') == "rmq"
        assert config.get('volttron', 'vip-address') == vip_address + ":" + vip_port
        assert config.get('volttron', 'instance-name').strip('"') == "test_rmq"
        assert config.get('volttron', 'bind-web-address') == "{}{}:{}".format("https://", get_hostname(), web_port)
        assert not _is_agent_installed("listener")
        assert not _is_agent_installed("platform_driver")
        assert not _is_agent_installed("platform_historian")
        assert not _is_agent_installed("vc ")
        assert not _is_agent_installed("vcp")
        assert not is_volttron_running(vhome)


@pytest.mark.skipif(not HAS_RMQ, reason='RabbitMQ is not setup')
@pytest.mark.timeout(RMQ_TIMEOUT)
def test_rmq_case_web_with_agents(monkeypatch):
    with create_vcfg_vhome() as vhome:
        monkeypatch.setenv("VOLTTRON_HOME", vhome)
        monkeypatch.setenv("RABBITMQ_CONF_ENV_FILE", "")
        config_path = os.path.join(vhome, "config")

        message_bus = "rmq"
        instance_name = "test_rmq"
        is_web_enabled = "Y"
        is_vc = "N"
        is_vcp = "Y"
        vc_hostname = "{}{}".format("https://", get_hostname())
        ip = '127.0.0.15'
        web_port = str(get_rand_port(ip, 8000, 9000))
        vc_port = str(get_rand_port(ip))
        vip_address = "tcp://" + ip
        vip_port = str(get_rand_port(ip))
        install_historian = "Y"
        install_driver = "Y"
        install_fake_device = "Y"
        install_listener = "Y"
        agent_autostart = "N"

        create_rmq_volttron_setup(vhome=vhome, env=os.environ, ssl_auth=True, instance_name=instance_name)

        vcfg_args = "\n".join([message_bus,
                               vip_address,
                               vip_port,
                               instance_name,
                               is_web_enabled,
                               web_port,
                               is_vc,
                               is_vcp,
                               vc_hostname,
                               vc_port,
                               agent_autostart,
                               install_historian,
                               agent_autostart,
                               install_driver,
                               install_fake_device,
                               agent_autostart,
                               install_listener,
                               agent_autostart
                               ])

        with subprocess.Popen(["vcfg", "--vhome", vhome],
                              env=os.environ,
                              cwd=os.environ.get("VOLTTRON_ROOT"),
                              stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              text=True
                              ) as vcfg:
            out, err = vcfg.communicate(vcfg_args)
        assert os.path.exists(config_path)
        config = ConfigParser()
        config.read(config_path)
        assert config.get('volttron', 'message-bus') == "rmq"
        assert config.get('volttron', 'vip-address') == vip_address + ":" + vip_port
        assert config.get('volttron', 'instance-name').strip('"') == "test_rmq"
        assert config.get('volttron', 'bind-web-address') == "{}{}:{}".format("https://", get_hostname(), web_port)
        assert _is_agent_installed("listener")
        assert _is_agent_installed("platform_driver")
        assert _is_agent_installed("platform_historian")
        assert not _is_agent_installed("vc ")
        assert _is_agent_installed("vcp")
        assert not is_volttron_running(vhome)


@pytest.mark.skipif(not HAS_RMQ, reason='RabbitMQ is not setup')
@pytest.mark.timeout(RMQ_TIMEOUT)
@pytest.mark.xfail
def test_rmq_case_web_vc(monkeypatch):
    with create_vcfg_vhome() as vhome:
        monkeypatch.setenv("VOLTTRON_HOME", vhome)
        monkeypatch.setenv("RABBITMQ_CONF_ENV_FILE", "")
        config_path = os.path.join(vhome, "config")

        message_bus = "rmq"
        instance_name = "test_rmq"
        ip = '127.0.0.15'
        vip_address = "tcp://" + ip
        vip_port = str(get_rand_port(ip))
        is_web_enabled = "Y"
        web_port = str(get_rand_port(ip, 8000, 9000))
        is_vc = "Y"
        is_vcp = "Y"
        install_historian = "N"
        install_driver = "N"
        install_listener = "N"
        agent_autostart = "N"

        create_rmq_volttron_setup(vhome=vhome, env=os.environ, ssl_auth=True, instance_name=instance_name)

        vcfg_args = "\n".join([message_bus,
                               vip_address,
                               vip_port,
                               instance_name,
                               is_web_enabled,
                               web_port,
                               is_vc,
                               agent_autostart,
                               is_vcp,
                               agent_autostart,
                               install_historian,
                               install_driver,
                               install_listener
                               ])

        with subprocess.Popen(["vcfg", "--vhome", vhome],
                              env=os.environ,
                              cwd=os.environ.get("VOLTTRON_ROOT"),
                              stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              text=True
                              ) as vcfg:
            out, err = vcfg.communicate(vcfg_args)

        assert os.path.exists(config_path)
        config = ConfigParser()
        config.read(config_path)
        assert config.get('volttron', 'message-bus') == "rmq"
        assert config.get('volttron', 'vip-address') == vip_address
        assert config.get('volttron', 'instance-name').strip('"') == "test_rmq"
        assert config.get('volttron', 'volttron-central-address') == "{}{}:{}".format(
            "https://", get_hostname(), web_port)
        assert config.get('volttron', 'bind-web-address') == "{}{}:{}".format(
            "https://", get_hostname(), web_port)
        assert not _is_agent_installed("listener")
        assert not _is_agent_installed("platform_driver")
        assert not _is_agent_installed("platform_historian")
        assert _is_agent_installed("vc ")
        assert _is_agent_installed("vcp")
        assert not is_volttron_running(vhome)


@pytest.mark.skipif(not HAS_RMQ, reason='RabbitMQ is not setup')
@pytest.mark.timeout(RMQ_TIMEOUT)
@pytest.mark.xfail
def test_rmq_case_web_vc_with_agents(monkeypatch):
    with create_vcfg_vhome() as vhome:
        monkeypatch.setenv("VOLTTRON_HOME", vhome)
        monkeypatch.setenv("RABBITMQ_CONF_ENV_FILE", "")
        config_path = os.path.join(vhome, "config")

        message_bus = "rmq"
        instance_name = "test_rmq"
        ip = '127.0.0.15'
        vip_address = "tcp://" + ip
        vip_port = str(get_rand_port(ip))
        is_web_enabled = "Y"
        web_port = str(get_rand_port(ip, 8000, 9000))
        is_vc = "Y"
        is_vcp = "Y"
        install_historian = "Y"
        install_driver = "Y"
        install_fake_device = "Y"
        install_listener = "Y"
        agent_autostart = "N"

        create_rmq_volttron_setup(vhome=vhome, env=os.environ, ssl_auth=True, instance_name=instance_name)

        vcfg_args = "\n".join([message_bus,
                               vip_address,
                               vip_port,
                               instance_name,
                               is_web_enabled,
                               web_port,
                               is_vc,
                               agent_autostart,
                               is_vcp,
                               agent_autostart,
                               install_historian,
                               agent_autostart,
                               install_driver,
                               install_fake_device,
                               agent_autostart,
                               install_listener,
                               agent_autostart
                               ])

        with subprocess.Popen(["vcfg", "--vhome", vhome],
                              env=os.environ,
                              cwd=os.environ.get("VOLTTRON_ROOT"),
                              stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              text=True
                              ) as vcfg:
            out, err = vcfg.communicate(vcfg_args)

        assert os.path.exists(config_path)
        config = ConfigParser()
        config.read(config_path)
        assert config.get('volttron', 'message-bus') == "rmq"
        assert config.get('volttron', 'vip-address') == vip_address + ":" + vip_port
        assert config.get('volttron', 'instance-name').strip('"') == "test_rmq"
        assert config.get('volttron', 'volttron-central-address') == "{}{}:{}".format(
            "https://", get_hostname(), web_port)
        assert config.get('volttron', 'bind-web-address') == "{}{}:{}".format(
            "https://", get_hostname(), web_port)
        assert _is_agent_installed("listener")
        assert _is_agent_installed("platform_driver")
        assert _is_agent_installed("platform_historian")
        assert _is_agent_installed("vc ")
        assert _is_agent_installed("vcp")
        assert not is_volttron_running(vhome)


def test_web_with_agents_volttron_running(monkeypatch, volttron_instance_web):
    vhome = volttron_instance_web.volttron_home
    monkeypatch.setenv("VOLTTRON_HOME", vhome)
    config_path = os.path.join(vhome, "config")

    is_running = "Y"
    is_vcp = "Y"
    default_vc_hostname = ""
    default_vc_port = ""
    install_historian = "Y"
    install_driver = "Y"
    install_fake_device = "Y"
    install_listener = "Y"
    agent_autostart = "N"
    agent_overwrite = "N"
    vcfg_args = "\n".join([is_running,
                           is_vcp,
                           default_vc_hostname,
                           default_vc_port,
                           agent_autostart,
                           install_historian,
                           agent_autostart,
                           install_driver,
                           install_fake_device,
                           agent_autostart,
                           install_listener,
                           agent_autostart
                           ])

    with subprocess.Popen(["vcfg", "--vhome", vhome],
                          env=os.environ,
                          stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          text=True
                          ) as vcfg:
        out, err = vcfg.communicate(vcfg_args)
    print(f"OUT: {out}")
    print(f"ERR: {err}")
    assert os.path.exists(config_path)
    config = ConfigParser()
    config.read(config_path)
    assert config.get('volttron', 'message-bus') == volttron_instance_web.messagebus
    if volttron_instance_web.ssl_auth is True and volttron_instance_web.messagebus == 'zmq':
        assert config.get('volttron', 'web-ssl-cert') == os.path.join(vhome, "certificates", "certs", "server0.crt")
        assert config.get('volttron', 'web-ssl-key') == os.path.join(vhome, "certificates", "private", "server0.pem")
    # if instance is running
    assert not _is_agent_installed("listener")
    # assert _is_agent_installed("platform_driver")
    # assert _is_agent_installed("platform_historian")
    # assert _is_agent_installed("vcp")
    assert is_volttron_running(vhome)

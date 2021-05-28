from bacpypes.debugging import bacpypes_debugging, ModuleLogger
from bacpypes.app import BIPSimpleApplication
from bacpypes.task import RecurringTask
from bacpypes.object import AnalogOutputObject, BinaryOutputObject
from bacpypes.service.device import LocalDeviceObject
from bacpypes.core import run

_debug = 0
_log = ModuleLogger(globals())

# test globals
test_av = None
test_bv = None
test_app = None

BACNET_SUBNET = "172.28.0.0/16"
BACNET_DEVICE_IP_ADDR = "172.28.5.1"
COOLING_VALVE_OUTPUT_COMMAND_OBJECT_ID = 3000107
GENERAL_EXHAUST_FAN_COMMAND_OBJECT_ID = 3000114



from bacpypes.debugging import bacpypes_debugging, ModuleLogger
from bacpypes.consolelogging import ConfigArgumentParser

from bacpypes.core import run, deferred
from bacpypes.iocb import IOCB

from bacpypes.pdu import Address
from bacpypes.apdu import SubscribeCOVRequest, SimpleAckPDU
from bacpypes.errors import ExecutionError
from bacpypes.service.cov import ChangeOfValueServices

@bacpypes_debugging
# TODO: Extend class to have more parent classes so that we can add more integration tests; look in BACpypes repo for more sophisticated applications
class SubscribeCOVApplication(BIPSimpleApplication, ChangeOfValueServices):
    def __init__(self, *args):
        if _debug: SubscribeCOVApplication._debug("__init__ %r", args)
        BIPSimpleApplication.__init__(self, *args)

    def send_subscription(self, context):
        if _debug: SubscribeCOVApplication._debug("send_subscription %r", context)

        # build a request
        request = SubscribeCOVRequest(
            subscriberProcessIdentifier=context.subscriberProcessIdentifier,
            monitoredObjectIdentifier=context.monitoredObjectIdentifier,
        )
        request.pduDestination = context.address

        # optional parameters
        if context.issueConfirmedNotifications is not None:
            request.issueConfirmedNotifications = context.issueConfirmedNotifications
        if context.lifetime is not None:
            request.lifetime = context.lifetime

        # make an IOCB
        iocb = IOCB(request)
        if _debug: SubscribeCOVApplication._debug("    - iocb: %r", iocb)

        # callback when it is acknowledged
        iocb.add_callback(self.subscription_acknowledged)

        # give it to the application
        this_application.request_io(iocb)

    def subscription_acknowledged(self, iocb):
        if _debug: SubscribeCOVApplication._debug("subscription_acknowledged %r", iocb)

        # do something for success
        if iocb.ioResponse:
            if _debug: SubscribeCOVApplication._debug("    - response: %r", iocb.ioResponse)

        # do something for error/reject/abort
        if iocb.ioError:
            if _debug: SubscribeCOVApplication._debug("    - error: %r", iocb.ioError)

    def do_ConfirmedCOVNotificationRequest(self, apdu):
        if _debug: SubscribeCOVApplication._debug("do_ConfirmedCOVNotificationRequest %r", apdu)

        # look up the process identifier
        context = subscription_contexts.get(apdu.subscriberProcessIdentifier, None)
        if not context or apdu.pduSource != context.address:
            if _debug: SubscribeCOVApplication._debug("    - no context")

            # this is turned into an ErrorPDU and sent back to the client
            raise ExecutionError('services', 'unknownSubscription')

        # now tell the context object
        context.cov_notification(apdu)

        # success
        response = SimpleAckPDU(context=apdu)
        if _debug: SubscribeCOVApplication._debug("    - simple_ack: %r", response)

        # return the result
        self.response(response)

    def do_UnconfirmedCOVNotificationRequest(self, apdu):
        if _debug: SubscribeCOVApplication._debug("do_UnconfirmedCOVNotificationRequest %r", apdu)

        # look up the process identifier
        context = subscription_contexts.get(apdu.subscriberProcessIdentifier, None)
        if not context or apdu.pduSource != context.address:
            if _debug: SubscribeCOVApplication._debug("    - no context")
            return

        # now tell the context object
        context.cov_notification(apdu)


@bacpypes_debugging
class TestAnalogOutputValueTask(RecurringTask):
    def __init__(self, interval):
        if _debug:
            TestAnalogOutputValueTask._debug("__init__ %r", interval)
        RecurringTask.__init__(self, interval * 1000)

        self.interval = interval
        self.test_values = [1.1, 1.2, 1.3]

    def process_task(self):
        if _debug:
            TestAnalogOutputValueTask._debug("process_task")
        global test_av

        n = self.test_values.pop(0)
        self.test_values.append(n)
        if _debug:
            TestAnalogOutputValueTask._debug("    - next_value: %r", n)
        test_av.presentValue = n


@bacpypes_debugging
class TestBinaryOutputValueTask(RecurringTask):
    def __init__(self, interval):
        if _debug:
            TestBinaryOutputValueTask._debug("__init__ %r", interval)
        RecurringTask.__init__(self, interval * 1000)

        self.interval = interval
        self.test_values = [False, True]

    def process_task(self):
        if _debug:
            TestBinaryOutputValueTask._debug("process_task")
        global test_bv

        n = self.test_values.pop(0)
        self.test_values.append(n)
        if _debug:
            TestBinaryOutputValueTask._debug("    - next_value: %r", n)
        test_bv.presentValue = n


def main():
    global test_app, test_av, test_bv

    # make a device
    this_device = LocalDeviceObject(objectIdentifier=500, vendorIdentifier=15)
    if _debug:
        _log.debug("    - this_device: %r", this_device)

    # add device to test application
    address = BACNET_DEVICE_IP_ADDR
    testapp = SubscribeCOVApplication(this_device, address)

    # the objectIdentifier's object instance (i.e. second value in tuple) should match the value in the corresponding Index column of the BACnet Driver's registry config
    test_av = AnalogOutputObject(
        objectIdentifier=("analogOutput", COOLING_VALVE_OUTPUT_COMMAND_OBJECT_ID),
        objectName="Building/FCB.Local Application.CLG-O",
        presentValue=1.0,
        statusFlags=[0, 0, 0, 0],
    )
    _log.debug("    - test_av: %r", test_av)
    testapp.add_object(test_av)

    test_bv = BinaryOutputObject(
        objectIdentifier=("binaryOutput", GENERAL_EXHAUST_FAN_COMMAND_OBJECT_ID),
        objectName="Building/FCB.Local Application.GEF-C",
        presentValue="inactive",
        statusFlags=[0, 0, 0, 0],
    )
    _log.debug("    - test_bv: %r", test_bv)
    testapp.add_object(test_bv)

    # TODO: make a third object that supports COV so that we can test COV of BACnet driver

    # run tasks
    test_av_task = TestAnalogOutputValueTask(5)
    test_av_task.process_task()

    test_bv_task = TestBinaryOutputValueTask(5)
    test_bv_task.process_task()

    run(1.0)


if __name__ == "__main__":
    main()

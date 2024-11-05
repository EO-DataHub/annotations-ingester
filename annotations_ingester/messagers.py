import dataclasses
import os
from abc import ABC, abstractmethod
from typing import Sequence

from pulsar import Client


class Messager[MSGTYPE](ABC):
    """
    This is just a stub to allow testing.

    A nascent implementation of messages is in a branch in the eodhup-utils repo.


    This is an abstract base class for creating 'messagers'. Messagers are classes which consume
    and/or produce catalogue Pulsar messages and entries in S3. Harvesters, transformers and
    ingesters can all be written as messagers. Messagers can be tested without any mocks.

    Messagers are triggered by some input and return a list of actions as output:
      * OutputFileAction:
          Write an entry to or delete an entry from the catalogue population bucket and emit it as
          an added, changed or deleted key in a Pulsar message.
      * S3UploadAction:
          Write a file to an S3 bucket.

    You should inherit from the correct subclass:
      * Producing Pulsar messages only (harvester):
          Inherit from Messager and implement process_msg(self, msg: <my obj>, **kwargs).
          Return a list of actions, probably OutputFileActions.

          Design your harvester to encapsulate each harvested entry as a <my obj> and call
          my_harvester.consume(my_obj).

          Write your tests to call process_msg directly.

      * Consuming Pulsar catalogue change messages only (ingester):
          Inherit from CatalogueChangeMessager and implement process_update and process_delete.
          Alternatively, use one of the subclasses defined here, such as
          CatalogueSTACChangeMessager, which will fetch the entry and ensure it's STAC before
          calling your subclass's process_stac_update method.

          Return an empty list if no further action is needed.

      * Consuming and producing Pulsar cataloge change messages (transformer):
          As for consuming Pulsar messages in the previous bullet except you should return a list
          of OutputFileActions.
    """

    class Action(ABC):  # noqa: B024
        """
        An Action is something that this class will do in response to a subclass's processing of
        a message.
        """

        pass

    @dataclasses.dataclass(kw_only=True)
    class S3Action(Action, ABC):
        file_body: str
        mime_type: str = "application/json"
        bucket: str = None  # Defaults to messager.output_bucket

    @dataclasses.dataclass(kw_only=True)
    class OutputFileAction(S3Action):
        """
        An OutputFileAction emits a file as a catalogue change action. Specifically:
        * If file_body is not None:
            * `file_body` is written to our output bucket in S3. The key will be
              <self.output_prefix>/<action.cat_path>. eg, this might be written to
              s3://eodhp-dev-catalogue-population/transformed/supported-datasets/ceda-stac-catalogue/
              `transformed/` is the output prefix.
            * After all other actions are completed, a catalogue change message is sent to Pulsar
              with the above key in `added_keys` or `changed_keys`.
        * If file_body is None the key defined above will be deleted from the bucket and put into
          `deleted_keys`.
        """

        cat_path: str

    @dataclasses.dataclass(kw_only=True)
    class Failures:
        """
        Describes the type of errors encountered during message processing.

        If 'permanent' is True then an error occured which will definitely not be resolved through
        retries. If 'temporary' is True then an error which is potentially resolvable this way
        occured. Both can be set.

        `key_permanent` and `key_temporary` are the same but for specific keys mentioned in
        catalogue change messages.
        """

        key_permanent: Sequence[str]
        key_temporary: Sequence[str]
        permanent: bool
        temporary: bool

    @dataclasses.dataclass(kw_only=True)
    class S3UploadAction(S3Action):
        """
        An S3UploadAction uploads a file to an S3 bucket at a specified key. `output_prefix` is not
        used and no Pulsar message is sent. `file_body` can be None to specify deletion.
        """

        key: str

    @abstractmethod
    def process_msg(self, msg: MSGTYPE) -> Sequence[Action]: ...


class CatalogueSTACChangeMessager(Messager, ABC):
    """
    This is just a stub to allow testing.

    A nascent implementation of messages is in a branch in the eodhup-utils repo.
    """

    @abstractmethod
    def process_stac_update(
        self,
        cat_path: str,
        stac: dict,
        **kwargs,
    ) -> Sequence[Messager.Action]: ...

    @abstractmethod
    def process_delete(
        self, bucket: str, key: str, id: str, source: str, target: str
    ) -> Sequence[Messager.Action]: ...

    def process_msg(self):
        pass

    def process_delete(self):
        pass

    def process_stac_update(
        self,
        cat_path: str,
        stac: dict,
        **kwargs,
    ) -> Sequence[Messager.Action]:
        pass




def run(messagers_dict: dict, subscription_name: str):

    pulsar_url = os.environ.get("PULSAR_URL")
    client = Client(pulsar_url)

    topics = messagers_dict.keys()

    consumer = client.subscribe(topic=topics, subscription_name=subscription_name)

    while True:
        pulsar_message = consumer.receive()

        messager = messagers_dict[pulsar_message.topic_name]

        failures = messager.consume(pulsar_message)

        if failures.permanent:
            pulsar_message.negative_acknowledge()
            raise Exception
        else:
            pulsar_message.acknowledge()

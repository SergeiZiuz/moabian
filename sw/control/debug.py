# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from .common import IDebugDecorator
import cv2
import os
import pathlib
import logging as log


SENSOR_IMG_ARG = "sensor_img"


class CallbackDecorator(IDebugDecorator):
    def __init__(self, config: dict):
        super().__init__(config)
        self.callbacks = []

    def addCallback(self, fn):
        self.callbacks.append(fn)

    def decorate(self, args):
        for callback in self.callbacks:
            callback(args)

class FileDecorator(CallbackDecorator):
    def __init__(self, config: dict):
        super().__init__(config)

        self.filename = self.config["filename"]
        self.disable = False

        # Create path to filename in case it doesn't exist
        dirname = os.path.dirname(self.filename)
        pathlib.Path(dirname).mkdir(parents=True, exist_ok=True)

        log.info(f"Saving camera stream to {self.filename}")

    def decorate(self, args):
        super().decorate(args)

        if self.disable:
            return

        # save frame as a JPEG file (with quality of 80)
        try:
            cv2.imwrite(self.filename, args[SENSOR_IMG_ARG], 
                    [cv2.IMWRITE_JPEG_QUALITY, 80])

        except Exception as ex:
            self.disable = True
            log.error(ex)
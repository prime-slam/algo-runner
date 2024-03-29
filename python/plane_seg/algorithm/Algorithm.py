from pathlib import Path
from .Config import Config

from typing import Collection
from shutil import rmtree
from docker.types import Mount

import docker
import numpy as np
import abc
import os

__all__ = ["Algorithm"]


class Algorithm(abc.ABC):
    @abc.abstractmethod
    def __init__(self, container_name: str, cfg_path: Path, pcd_path: Path, **kwargs):
        self.container_name = container_name
        self.cfg_path = cfg_path
        self.pcd_path = pcd_path
        self._alg_input_dir = Path("alg_input")
        self._alg_output_dir = Path("output")
        self._alg_artifact_name = None
        self._cfg = None
        self._parameter_list = ()

    @abc.abstractmethod
    def _preprocess_input(self) -> Collection[str]:
        pass

    @abc.abstractmethod
    def _output_to_labels(self, output_path: Path) -> np.ndarray:
        pass

    @abc.abstractmethod
    def _clear_artifacts(self):
        pass

    def _evaluate_algorithm(self, input_parameters: Collection[str]) -> Path:
        client = docker.from_env()
        input_mount = Mount(
            target="/app/build/input",
            source=str(self._alg_input_dir.absolute()),
            type="bind",
        )
        output_mount = Mount(
            target="/app/build/output",
            source=str(self._alg_output_dir.absolute()),
            type="bind",
        )

        client.containers.run(
            self.container_name,
            " ".join(input_parameters),
            mounts=[input_mount, output_mount],
        )

        return self._alg_output_dir / self._alg_artifact_name

    def load_config(self, cfg_path: Path = None):
        self._cfg = Config(cfg_path or self.cfg_path, self._parameter_list)

    def run(self) -> np.ndarray:
        self.load_config()

        if self._alg_input_dir.exists():
            rmtree(self._alg_input_dir)
        os.mkdir(self._alg_input_dir)

        parameter_list = self._preprocess_input()

        if os.path.exists(self._alg_output_dir):
            rmtree(self._alg_output_dir)
        os.mkdir(self._alg_output_dir)

        try:
            output_path = self._evaluate_algorithm(parameter_list)
            labels = self._output_to_labels(output_path)
        finally:
            self._clear_artifacts()

        return labels

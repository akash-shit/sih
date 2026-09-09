import unittest
from pathlib import Path
from unittest import mock

import app.config as config


class RemoteClipConfigTests(unittest.TestCase):
    def test_requires_local_remoteclip_checkpoint(self):
        missing_path = Path("this-checkpoint-does-not-exist.pt").resolve()
        with mock.patch.object(config, "REMOTECLIP_CHECKPOINT", missing_path):
            with self.assertRaisesRegex(RuntimeError, "RemoteCLIP checkpoint not found"):
                config.validate_remoteclip_config()


if __name__ == "__main__":
    unittest.main()

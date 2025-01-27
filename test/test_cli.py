from abstract_isa_test import AbstractIsaTest

class TestArcTransfer(AbstractIsaTest):

    def test_init_cli(self, ):

        args = self.args + [
            "pack",
            "--plugin","isa",
        ]
        self.cli.invoke(args)
from abstract_isa_test import AbstractIsaTest

class TestArcTransfer(AbstractIsaTest):

    def test_init_cli(self, project_1, tmp_path):
        project_identifier = f"Project:{project_1.getId()}"

        args = self.args + [
            "pack",
            "--plugin","isa",
            project_identifier,
            str(tmp_path)
        ]
        self.cli.invoke(args)

        print(tmp_path)
        assert (tmp_path / "i_investigation.txt").exists()

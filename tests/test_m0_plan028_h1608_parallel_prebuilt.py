"""H1608 source-guarded one native scene per independent Action, no rebuild."""
import pathlib
import unittest
R=pathlib.Path(__file__).resolve().parents[1]/".github/workflows"
class ReuseNativeParallelTest(unittest.TestCase):
    def test_two_independent_push_actions_one_network_each(self):
        n=(R/"m0-plan028-h1608-normal-auto-path.yml").read_text()
        g=(R/"m0-plan028-h1608-game4-fixed6-path.yml").read_text()
        y=(R/"m0-plan028-h1608-prebuilt-native-path.yml").read_text()
        self.assertIn("public_mode: normal",n)
        self.assertIn("game_fec: off",n)
        self.assertIn("public_mode: game4",g)
        self.assertIn("game_fec: fixed6",g)
        for x in (n,g):
            self.assertIn("uses: ./.github/workflows/m0-plan028-h1608-prebuilt-native-path.yml",x)
            self.assertIn("paths:",x)
        self.assertEqual(y.count("bash tools/m0-v4-public-real-linux-netns.sh linux-product"),1)
        for text in ('run-id: 43027983611','git diff --name-only',
           'rust_native_fec_acceleration', 'H1608_THREE_ORIGINAL_GO_RUST_ELF_NATIVE_ISAL_SHA256_SAME_PRODUCT_SOURCE_PASS',
           'WBD_V4_PUBLIC_AUTO_IP=1 WBD_V4_PUBLIC_PATH_SWITCH=1',
           'H1608_ONE_PREBUILT_REAL_NATIVE_PATH_PASS_SCOPED'):
            self.assertIn(text,y)
        self.assertNotIn('cargo build',y)
        self.assertNotIn('go build',y)
        self.assertNotIn('wsl.exe',y)
if __name__=="__main__":unittest.main()

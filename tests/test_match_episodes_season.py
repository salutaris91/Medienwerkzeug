import unittest
import gui.server as server
from gui.server import GUIRequestHandler


class DummyHandler:
    def __init__(self):
        self.sent_json = None

    def send_json(self, data):
        self.sent_json = data


class TestMatchEpisodesSeason(unittest.TestCase):
    def setUp(self):
        self.orig_fetch_tvdb = server.mw_metadata.fetch_tvdb
        self.dummy = DummyHandler()

    def tearDown(self):
        server.mw_metadata.fetch_tvdb = self.orig_fetch_tvdb

    def _make_ak1_episodes(self):
        """Build episode list S01E01 ... S11E24 with absolute_number starting at 1."""
        episodes = {}
        abs_num = 1
        for s in range(1, 12):
            for e in range(1, 25):
                key = f"S{s:02d}E{e:02d}"
                episodes[key] = {
                    "title": f"The Walking Dead {key}",
                    "absolute_number": abs_num,
                }
                abs_num += 1
        return episodes

    def test_ak1_season_aware_match_precedence_over_absolute_number(self):
        """AK1: Datei The.Walking.Dead.S11E01.GERMAN.mkv -> S11E01 (not S01E01 which has absolute_number=1)."""
        episodes = self._make_ak1_episodes()
        server.mw_metadata.fetch_tvdb = lambda show_id, season, lang: episodes

        params = {
            "provider": "tvdb",
            "show_id": "153021",
            "season": "all",
            "filenames": ["The.Walking.Dead.S11E01.GERMAN.mkv"],
        }
        GUIRequestHandler.handle_api_match_episodes(self.dummy, params)
        matches = (self.dummy.sent_json or {}).get("matches", {})
        self.assertEqual(matches.get("The.Walking.Dead.S11E01.GERMAN.mkv"), "S11E01")

    def test_ak2_season_match_ordering_independent(self):
        """AK2: Datei ...S11E07... -> S11E07, even if S02E07 is earlier in the list."""
        episodes = self._make_ak1_episodes()
        server.mw_metadata.fetch_tvdb = lambda show_id, season, lang: episodes

        params = {
            "provider": "tvdb",
            "show_id": "153021",
            "season": "all",
            "filenames": ["The.Walking.Dead.S11E07.GERMAN.mkv"],
        }
        GUIRequestHandler.handle_api_match_episodes(self.dummy, params)
        matches = (self.dummy.sent_json or {}).get("matches", {})
        self.assertEqual(matches.get("The.Walking.Dead.S11E07.GERMAN.mkv"), "S11E07")

    def test_ak3_season_present_but_episode_missing_returns_none(self):
        """AK3: Season 11 is present (S11E01..S11E10), but episode 14 missing -> None."""
        episodes = {}
        for e in range(1, 11):
            episodes[f"S01E{e:02d}"] = {"title": f"Episode S01E{e:02d}", "absolute_number": e}
        for e in range(1, 11):
            episodes[f"S11E{e:02d}"] = {"title": f"Episode S11E{e:02d}", "absolute_number": 10 + e}
        server.mw_metadata.fetch_tvdb = lambda show_id, season, lang: episodes

        params = {
            "provider": "tvdb",
            "show_id": "153021",
            "season": "all",
            "filenames": ["The.Walking.Dead.S11E14.GERMAN.mkv"],
        }
        GUIRequestHandler.handle_api_match_episodes(self.dummy, params)
        matches = (self.dummy.sent_json or {}).get("matches", {})
        self.assertIn("The.Walking.Dead.S11E14.GERMAN.mkv", matches)
        self.assertIsNone(matches.get("The.Walking.Dead.S11E14.GERMAN.mkv"))

    def test_ak4_cross_syntax_season_and_episode(self):
        """AK4: Datei ...11x01... against AK1 list -> S11E01."""
        episodes = self._make_ak1_episodes()
        server.mw_metadata.fetch_tvdb = lambda show_id, season, lang: episodes

        params = {
            "provider": "tvdb",
            "show_id": "153021",
            "season": "all",
            "filenames": ["The.Walking.Dead.11x01.GERMAN.mkv"],
        }
        GUIRequestHandler.handle_api_match_episodes(self.dummy, params)
        matches = (self.dummy.sent_json or {}).get("matches", {})
        self.assertEqual(matches.get("The.Walking.Dead.11x01.GERMAN.mkv"), "S11E01")

    def test_ak5_fallback_to_single_season_numerical_keys(self):
        """AK5: Single season list with keys "1"..."23", file ...S11E01... -> "1"."""
        episodes = {str(i): {"title": f"Episode {i}"} for i in range(1, 24)}
        server.mw_metadata.fetch_tvdb = lambda show_id, season, lang: episodes

        params = {
            "provider": "tvdb",
            "show_id": "153021",
            "season": "1",
            "filenames": ["The.Walking.Dead.S11E01.GERMAN.mkv"],
        }
        GUIRequestHandler.handle_api_match_episodes(self.dummy, params)
        matches = (self.dummy.sent_json or {}).get("matches", {})
        self.assertEqual(matches.get("The.Walking.Dead.S11E01.GERMAN.mkv"), "1")

    def test_ak6_fallback_to_year_based_season_keys(self):
        """AK6: Year-based list S2010E39, S2011E40, file ...S01E39... -> S2010E39."""
        episodes = {
            "S2010E39": {"title": "In der Ruhe liegt die Kraft", "date": "2010-01-01"},
            "S2011E40": {"title": "Folge 40", "date": "2011-01-01"},
        }
        server.mw_metadata.fetch_tvdb = lambda show_id, season, lang: episodes

        params = {
            "provider": "tvdb",
            "show_id": "249482",
            "season": "all",
            "filenames": ["Elefant_Tiger_Co_S01E39.mp4"],
        }
        GUIRequestHandler.handle_api_match_episodes(self.dummy, params)
        matches = (self.dummy.sent_json or {}).get("matches", {})
        self.assertEqual(matches.get("Elefant_Tiger_Co_S01E39.mp4"), "S2010E39")

    def test_ak7_existing_match_episodes_test_case(self):
        """AK7: Test case from test_utils.py (381 -> S2010E39, S01E05 -> S01E05)."""
        episodes = {
            "S2010E39": {"title": "In der Ruhe liegt die Kraft", "date": "2010-01-01", "absolute_number": 381},
            "S01E05": {"title": "Anderer Titel", "date": "2003-05-01", "absolute_number": 5},
        }
        server.mw_metadata.fetch_tvdb = lambda show_id, season, lang: episodes

        params = {
            "provider": "tvdb",
            "show_id": "249482",
            "season": "all",
            "filenames": [
                "Elefant,_Tiger_&_Co._In_der_Ruhe_liegt_die_Kraft_(381)_2026.mp4",
                "Elefant_Tiger_Co_S01E05_Test.mp4",
            ],
        }
        GUIRequestHandler.handle_api_match_episodes(self.dummy, params)
        matches = (self.dummy.sent_json or {}).get("matches", {})
        self.assertEqual(matches.get("Elefant,_Tiger_&_Co._In_der_Ruhe_liegt_die_Kraft_(381)_2026.mp4"), "S2010E39")
        self.assertEqual(matches.get("Elefant_Tiger_Co_S01E05_Test.mp4"), "S01E05")

    def test_ak8_leading_zeros_handling(self):
        """AK8: Leading zeroes: S11E1 and s11e01 against key S11E01 -> S11E01."""
        episodes = {"S11E01": {"title": "Acheron: Part I"}}
        server.mw_metadata.fetch_tvdb = lambda show_id, season, lang: episodes

        params = {
            "provider": "tvdb",
            "show_id": "153021",
            "season": "all",
            "filenames": [
                "The.Walking.Dead.S11E1.GERMAN.mkv",
                "the.walking.dead.s11e01.german.mkv",
            ],
        }
        GUIRequestHandler.handle_api_match_episodes(self.dummy, params)
        matches = (self.dummy.sent_json or {}).get("matches", {})
        self.assertEqual(matches.get("The.Walking.Dead.S11E1.GERMAN.mkv"), "S11E01")
        self.assertEqual(matches.get("the.walking.dead.s11e01.german.mkv"), "S11E01")

    def test_ak10_year_in_parentheses_vs_absolute_number_parentheses(self):
        """AK10: (2010) is a year (ignored for episode number, S11E01 matches).

        (381) is an absolute number (takes precedence over S11E01, matching via bracket path).
        """
        episodes = self._make_ak1_episodes()
        # Add a special entry for absolute_number 381
        episodes["S2010E39"] = {"title": "Special 381", "absolute_number": 381}
        server.mw_metadata.fetch_tvdb = lambda show_id, season, lang: episodes

        params = {
            "provider": "tvdb",
            "show_id": "153021",
            "season": "all",
            "filenames": [
                "The Walking Dead (2010) - S11E01 - Acheron.mkv",
                "Show (381) S11E01.mkv",
            ],
        }
        GUIRequestHandler.handle_api_match_episodes(self.dummy, params)
        matches = (self.dummy.sent_json or {}).get("matches", {})
        # File with (2010) treats 2010 as year and uses season S11E01 -> S11E01
        self.assertEqual(matches.get("The Walking Dead (2010) - S11E01 - Acheron.mkv"), "S11E01")
        # File with (381) treats 381 as absolute episode number -> matches S2010E39 via bracket path
        self.assertEqual(matches.get("Show (381) S11E01.mkv"), "S2010E39")


    def test_r6_ak1_spelled_out_season_episode_matching(self):
        """AK1: Liste S01E01 ... S11E24, Datei The Walking Dead Staffel 11 Folge 14.mkv -> S11E14."""
        episodes = self._make_ak1_episodes()
        server.mw_metadata.fetch_tvdb = lambda show_id, season, lang: episodes

        filename = "The Walking Dead Staffel 11 Folge 14.mkv"
        params = {
            "provider": "tvdb",
            "show_id": "153021",
            "season": "all",
            "filenames": [filename],
        }
        GUIRequestHandler.handle_api_match_episodes(self.dummy, params)
        matches = (self.dummy.sent_json or {}).get("matches", {})
        self.assertEqual(matches.get(filename), "S11E14")

    def test_r6_ak2_spelled_out_syntax_variants(self):
        """AK2: Schreibweisen -> S11E14: Dots, hyphens, underscores, uppercase."""
        episodes = self._make_ak1_episodes()
        server.mw_metadata.fetch_tvdb = lambda show_id, season, lang: episodes

        filenames = [
            "The.Walking.Dead.Staffel.11.Folge.14.mkv",
            "The Walking Dead - Season 11 - Episode 14.mkv",
            "twd_staffel_11_ep_14.mkv",
            "THE WALKING DEAD STAFFEL 11 FOLGE 14.mkv",
        ]
        params = {
            "provider": "tvdb",
            "show_id": "153021",
            "season": "all",
            "filenames": filenames,
        }
        GUIRequestHandler.handle_api_match_episodes(self.dummy, params)
        matches = (self.dummy.sent_json or {}).get("matches", {})
        for fn in filenames:
            self.assertEqual(matches.get(fn), "S11E14", f"Failed for {fn}")

    def test_r6_ak3_season_present_but_episode_missing_returns_none(self):
        """AK3: Liste mit S11E01..S11E10 und S01E01..S01E20, Datei ...Staffel 11 Folge 14... -> None (R2)."""
        episodes = {}
        for e in range(1, 21):
            episodes[f"S01E{e:02d}"] = {"title": f"S01E{e:02d}", "absolute_number": e}
        for e in range(1, 11):
            episodes[f"S11E{e:02d}"] = {"title": f"S11E{e:02d}", "absolute_number": 20 + e}
        server.mw_metadata.fetch_tvdb = lambda show_id, season, lang: episodes

        filename = "The Walking Dead Staffel 11 Folge 14.mkv"
        params = {
            "provider": "tvdb",
            "show_id": "153021",
            "season": "all",
            "filenames": [filename],
        }
        GUIRequestHandler.handle_api_match_episodes(self.dummy, params)
        matches = (self.dummy.sent_json or {}).get("matches", {})
        self.assertIn(filename, matches)
        self.assertIsNone(matches.get(filename))

    def test_r6_ak4_r3a_single_season_numerical_keys(self):
        """AK4: Einzelstaffel-Liste '1'..'23', Datei ...Staffel 11 Folge 14... -> '14' (R3a).

        Zusätzlich: ...S11E14... gegen dieselbe Liste -> '14' (unverändert).
        """
        episodes = {str(i): {"title": f"Episode {i}"} for i in range(1, 24)}
        server.mw_metadata.fetch_tvdb = lambda show_id, season, lang: episodes

        filenames = [
            "The Walking Dead Staffel 11 Folge 14.mkv",
            "The.Walking.Dead.S11E14.GERMAN.mkv",
        ]
        params = {
            "provider": "tvdb",
            "show_id": "153021",
            "season": "1",
            "filenames": filenames,
        }
        GUIRequestHandler.handle_api_match_episodes(self.dummy, params)
        matches = (self.dummy.sent_json or {}).get("matches", {})
        self.assertEqual(matches.get("The Walking Dead Staffel 11 Folge 14.mkv"), "14")
        self.assertEqual(matches.get("The.Walking.Dead.S11E14.GERMAN.mkv"), "14")

    def test_r6_ak5_unchanged_legacy_paths(self):
        """AK5: Unverändert: Folge 381.mkv, Show (381).mkv, Show Staffel 2.mkv, Show Staffel 2 (Folge 14).mkv."""
        episodes = self._make_ak1_episodes()
        episodes["S2010E39"] = {"title": "Special 381", "absolute_number": 381}
        server.mw_metadata.fetch_tvdb = lambda show_id, season, lang: episodes

        filenames = [
            "Folge 381.mkv",
            "Show (381).mkv",
            "Show Staffel 2.mkv",
            "Show Staffel 2 (Folge 14).mkv",
        ]
        params = {
            "provider": "tvdb",
            "show_id": "153021",
            "season": "all",
            "filenames": filenames,
        }
        GUIRequestHandler.handle_api_match_episodes(self.dummy, params)
        matches = (self.dummy.sent_json or {}).get("matches", {})
        self.assertEqual(matches.get("Folge 381.mkv"), "S2010E39")
        self.assertEqual(matches.get("Show (381).mkv"), "S2010E39")
        self.assertEqual(matches.get("Show Staffel 2.mkv"), "S01E02")
        self.assertEqual(matches.get("Show Staffel 2 (Folge 14).mkv"), "S01E14")

    def test_r6_ak6_distance_limit_exceeded_falls_back_to_legacy(self):
        """AK6: Abstandsgrenze: Staffel 11 <mehr als 40 Zeichen Text> Folge 14 -> R6 greift nicht."""
        episodes = self._make_ak1_episodes()
        server.mw_metadata.fetch_tvdb = lambda show_id, season, lang: episodes

        long_distance_filename = "Staffel 11 " + ("x" * 41) + " Folge 14.mkv"
        params = {
            "provider": "tvdb",
            "show_id": "153021",
            "season": "all",
            "filenames": [long_distance_filename],
        }
        GUIRequestHandler.handle_api_match_episodes(self.dummy, params)
        matches = (self.dummy.sent_json or {}).get("matches", {})
        self.assertEqual(matches.get(long_distance_filename), "S01E11")
        self.assertNotEqual(matches.get(long_distance_filename), "S11E14")

    def test_r6_ak7_sxxeyy_precedence_over_spelled_out(self):
        """AK7: Vorrang: The.Walking.Dead.S10E18.Staffel.11.Folge.14.mkv -> S10E18."""
        episodes = self._make_ak1_episodes()
        server.mw_metadata.fetch_tvdb = lambda show_id, season, lang: episodes

        filename = "The.Walking.Dead.S10E18.Staffel.11.Folge.14.mkv"
        params = {
            "provider": "tvdb",
            "show_id": "153021",
            "season": "all",
            "filenames": [filename],
        }
        GUIRequestHandler.handle_api_match_episodes(self.dummy, params)
        matches = (self.dummy.sent_json or {}).get("matches", {})
        self.assertEqual(matches.get(filename), "S10E18")


if __name__ == "__main__":
    unittest.main()

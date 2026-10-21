# Development measurement scope

The first raw trial (`pan_cost_trial01_with_headless_jobs.json`) overlapped our headless component tests. The second (`pan_cost_washes_and_multiline.json`) ran after those tests, but unrelated application load was not controlled. Its old `other_godot_tests_running` field refers only to our test workers; it does not establish an isolated GPU or an empty desktop. Original reports remain unchanged.

Both trials toggle only the new mountain underlays in the same development game and camera path; neither compares two released binaries. The later contour mesh trial has its own folder and process snapshot. Frame samples include cache rebuilds. Windows results do not establish physical Android performance.

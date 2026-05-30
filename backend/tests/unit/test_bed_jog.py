"""Unit tests for the bed-jog and home-axes endpoints (#791).

Tests:
  POST /api/v1/printers/{printer_id}/bed-jog?distance=<mm>&force=<bool>
  POST /api/v1/printers/{printer_id}/home-axes?axes=<z|xy|all>
"""

from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

from backend.app.api.routes.printers import _axis_travel_mm


@pytest.mark.parametrize(
    ("model", "travel"),
    [
        ("A1 Mini", (180, 180, 180)),
        ("A1", (256, 256, 256)),
        ("X1", (256, 256, 256)),
        ("X1C", (256, 256, 256)),
        ("X1E", (256, 256, 256)),
        ("P1P", (256, 256, 256)),
        ("P1S", (256, 256, 256)),
        ("P2S", (256, 256, 256)),
        ("H2D", (325, 320, 325)),
        ("H2D Pro", (325, 320, 325)),
        ("H2C", (305, 320, 325)),
        ("H2S", (340, 320, 340)),
        ("X2D", (256, 256, 260)),
    ],
)
def test_axis_travel_uses_supported_printer_profile(model: str, travel: tuple[int, int, int]):
    assert tuple(_axis_travel_mm(model, axis) for axis in ("x", "y", "z")) == travel


class TestBedJogAPI:
    @pytest.mark.asyncio
    async def test_bed_jog_not_found(self, async_client: AsyncClient):
        response = await async_client.post("/api/v1/printers/99999/bed-jog?distance=10")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_bed_jog_zero_distance_rejected(self, async_client: AsyncClient, printer_factory):
        printer = await printer_factory(name="P1")
        response = await async_client.post(f"/api/v1/printers/{printer.id}/bed-jog?distance=0")
        assert response.status_code == 400
        assert "distance" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_bed_jog_too_large_rejected(self, async_client: AsyncClient, printer_factory):
        printer = await printer_factory(name="P1")
        response = await async_client.post(f"/api/v1/printers/{printer.id}/bed-jog?distance=500")
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_bed_jog_not_connected(self, async_client: AsyncClient, printer_factory):
        printer = await printer_factory(name="Disconnected")
        with patch("backend.app.api.routes.printers.printer_manager") as mock_pm:
            mock_pm.get_client.return_value = None
            response = await async_client.post(f"/api/v1/printers/{printer.id}/bed-jog?distance=10")
            assert response.status_code == 400
            assert "not connected" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_bed_jog_send_failure(self, async_client: AsyncClient, printer_factory):
        printer = await printer_factory(name="P1")
        mock_client = MagicMock()
        mock_client.send_gcode.return_value = False
        with patch("backend.app.api.routes.printers.printer_manager") as mock_pm:
            mock_pm.get_client.return_value = mock_client
            response = await async_client.post(f"/api/v1/printers/{printer.id}/bed-jog?distance=10")
            assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_bed_jog_success_without_force(self, async_client: AsyncClient, printer_factory):
        """When force=false the M211 guard lines must not be emitted."""
        printer = await printer_factory(name="P1")
        mock_client = MagicMock()
        mock_client.send_gcode.return_value = True
        with patch("backend.app.api.routes.printers.printer_manager") as mock_pm:
            mock_pm.get_client.return_value = mock_client
            response = await async_client.post(f"/api/v1/printers/{printer.id}/bed-jog?distance=10&force=false")
            assert response.status_code == 200
            sent_gcode = mock_client.send_gcode.call_args[0][0]
            assert "G91" in sent_gcode
            assert "G1 Z10.00" in sent_gcode
            assert "G90" in sent_gcode
            assert "M211" not in sent_gcode

    @pytest.mark.asyncio
    async def test_bed_jog_success_with_force(self, async_client: AsyncClient, printer_factory):
        """force=true must wrap the move in M211 S0 / M211 S1."""
        printer = await printer_factory(name="P1")
        mock_client = MagicMock()
        mock_client.send_gcode.return_value = True
        with patch("backend.app.api.routes.printers.printer_manager") as mock_pm:
            mock_pm.get_client.return_value = mock_client
            response = await async_client.post(f"/api/v1/printers/{printer.id}/bed-jog?distance=-5&force=true")
            assert response.status_code == 200
            sent_gcode = mock_client.send_gcode.call_args[0][0]
            lines = sent_gcode.splitlines()
            assert lines[0] == "M211 S0"
            assert lines[-1] == "M211 S1"
            assert "G1 Z-5.00" in sent_gcode

    @pytest.mark.asyncio
    @pytest.mark.parametrize("model", ["X1C", "P1S", "H2D", "H2S", "H2C", "P2S"])
    async def test_bed_jog_bed_on_z_models_pass_distance_through(
        self, async_client: AsyncClient, printer_factory, model
    ):
        """On bed-on-Z printers the UI's signed distance maps directly to the
        G-code Z value — UI "Up" (negative) → bed up (G1 Z-) → less gap."""
        printer = await printer_factory(name=f"Test-{model}", model=model)
        mock_client = MagicMock()
        mock_client.send_gcode.return_value = True
        with patch("backend.app.api.routes.printers.printer_manager") as mock_pm:
            mock_pm.get_client.return_value = mock_client
            response = await async_client.post(f"/api/v1/printers/{printer.id}/bed-jog?distance=-10")
            assert response.status_code == 200
            sent_gcode = mock_client.send_gcode.call_args[0][0]
            # Negative distance from the UI → negative Z in the G-code: bed moves up.
            assert "G1 Z-10.00" in sent_gcode, f"{model}: expected G1 Z-10.00 in gcode, got {sent_gcode!r}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "model",
        ["A1", "A1 Mini", "A1MINI", "A1-MINI", "N1", "N2S"],  # display names + internal codes
    )
    async def test_bed_jog_a1_models_invert_z_sign(self, async_client: AsyncClient, printer_factory, model):
        """#1334 regression: on bed-slinger A1 / A1 Mini the Z axis is the
        TOOLHEAD, not the bed. The frontend sends negative distance for "Up"
        (decrease gap) expecting bed-on-Z semantics, but ``G1 Z-`` on A1
        drives the nozzle DOWN into the bed. The backend must invert the
        sign on these models so "Up" still decreases the gap by raising the
        toolhead (G1 Z+) rather than crashing it."""
        printer = await printer_factory(name=f"Test-{model}", model=model)
        mock_client = MagicMock()
        mock_client.send_gcode.return_value = True
        with patch("backend.app.api.routes.printers.printer_manager") as mock_pm:
            mock_pm.get_client.return_value = mock_client
            # UI sends -10 for "Up" → backend must emit G1 Z+10 on A1.
            response = await async_client.post(f"/api/v1/printers/{printer.id}/bed-jog?distance=-10")
            assert response.status_code == 200
            sent_gcode = mock_client.send_gcode.call_args[0][0]
            assert "G1 Z10.00" in sent_gcode, f"{model}: expected G1 Z10.00 in gcode, got {sent_gcode!r}"
            assert "G1 Z-10" not in sent_gcode, f"{model}: must NOT emit negative Z for a UI 'Up' click"

    @pytest.mark.asyncio
    async def test_bed_jog_a1_down_arrow_drops_toolhead(self, async_client: AsyncClient, printer_factory):
        """Symmetric to the regression test: UI "Down" (positive distance,
        increase gap) on A1 must lower the toolhead via G1 Z-."""
        printer = await printer_factory(name="A1-Mini-Test", model="A1 Mini")
        mock_client = MagicMock()
        mock_client.send_gcode.return_value = True
        with patch("backend.app.api.routes.printers.printer_manager") as mock_pm:
            mock_pm.get_client.return_value = mock_client
            response = await async_client.post(f"/api/v1/printers/{printer.id}/bed-jog?distance=10")
            assert response.status_code == 200
            sent_gcode = mock_client.send_gcode.call_args[0][0]
            assert "G1 Z-10.00" in sent_gcode


class TestAxisJogAPI:
    @pytest.mark.asyncio
    async def test_axis_jog_not_found(self, async_client: AsyncClient):
        response = await async_client.post("/api/v1/printers/99999/axis-jog?axis=x&distance=10")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_axis_jog_invalid_axis(self, async_client: AsyncClient, printer_factory):
        printer = await printer_factory(name="P1")
        response = await async_client.post(f"/api/v1/printers/{printer.id}/axis-jog?axis=e&distance=10")
        assert response.status_code == 400
        assert "axis" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_axis_jog_zero_distance_rejected(self, async_client: AsyncClient, printer_factory):
        printer = await printer_factory(name="P1")
        response = await async_client.post(f"/api/v1/printers/{printer.id}/axis-jog?axis=x&distance=0")
        assert response.status_code == 400
        assert "distance" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_axis_jog_not_connected(self, async_client: AsyncClient, printer_factory):
        printer = await printer_factory(name="Disconnected")
        with patch("backend.app.api.routes.printers.printer_manager") as mock_pm:
            mock_pm.get_client.return_value = None
            response = await async_client.post(f"/api/v1/printers/{printer.id}/axis-jog?axis=x&distance=10")
            assert response.status_code == 400
            assert "not connected" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_axis_jog_xy_success_without_force(self, async_client: AsyncClient, printer_factory):
        printer = await printer_factory(name="P1")
        mock_client = MagicMock()
        mock_client.send_gcode.return_value = True
        with patch("backend.app.api.routes.printers.printer_manager") as mock_pm:
            mock_pm.get_client.return_value = mock_client
            response = await async_client.post(f"/api/v1/printers/{printer.id}/axis-jog?axis=x&distance=-5")
            assert response.status_code == 200
            sent_gcode = mock_client.send_gcode.call_args[0][0]
            assert "G91" in sent_gcode
            assert "G1 X-5.00 F3000" in sent_gcode
            assert "G90" in sent_gcode
            assert "M211" not in sent_gcode

    @pytest.mark.asyncio
    async def test_axis_jog_xy_success_with_force(self, async_client: AsyncClient, printer_factory):
        printer = await printer_factory(name="P1")
        mock_client = MagicMock()
        mock_client.send_gcode.return_value = True
        with patch("backend.app.api.routes.printers.printer_manager") as mock_pm:
            mock_pm.get_client.return_value = mock_client
            response = await async_client.post(f"/api/v1/printers/{printer.id}/axis-jog?axis=y&distance=25&force=true")
            assert response.status_code == 200
            sent_gcode = mock_client.send_gcode.call_args[0][0]
            lines = sent_gcode.splitlines()
            assert lines[0] == "M211 S0"
            assert lines[-1] == "M211 S1"
            assert "G1 Y25.00 F3000" in sent_gcode

    @pytest.mark.asyncio
    async def test_axis_jog_z_reuses_bed_slinger_safety(self, async_client: AsyncClient, printer_factory):
        printer = await printer_factory(name="A1-Mini-Test", model="A1 Mini")
        mock_client = MagicMock()
        mock_client.send_gcode.return_value = True
        with patch("backend.app.api.routes.printers.printer_manager") as mock_pm:
            mock_pm.get_client.return_value = mock_client
            response = await async_client.post(f"/api/v1/printers/{printer.id}/axis-jog?axis=z&distance=-10")
            assert response.status_code == 200
            sent_gcode = mock_client.send_gcode.call_args[0][0]
            assert "G1 Z10.00 F600" in sent_gcode
            assert "G1 Z-10" not in sent_gcode

    @pytest.mark.asyncio
    async def test_axis_jog_respects_custom_speed_and_motion_limit(self, async_client: AsyncClient, printer_factory):
        printer = await printer_factory(name="P1")
        mock_client = MagicMock()
        mock_client.send_gcode.return_value = True
        with patch("backend.app.api.routes.printers.printer_manager") as mock_pm:
            mock_pm.get_client.return_value = mock_client
            response = await async_client.post(
                f"/api/v1/printers/{printer.id}/axis-jog?axis=y&distance=20&speed=4200&limit=25"
            )
            assert response.status_code == 200
            sent_gcode = mock_client.send_gcode.call_args[0][0]
            assert "G1 Y20.00 F4200" in sent_gcode

    @pytest.mark.asyncio
    async def test_axis_jog_rejects_distance_over_motion_limit(self, async_client: AsyncClient, printer_factory):
        printer = await printer_factory(name="P1")
        response = await async_client.post(f"/api/v1/printers/{printer.id}/axis-jog?axis=x&distance=20&limit=10")
        assert response.status_code == 400
        assert "distance" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_axis_jog_rejects_distance_over_a1_mini_travel(self, async_client: AsyncClient, printer_factory):
        printer = await printer_factory(name="A1-Mini-Test", model="A1 Mini")
        response = await async_client.post(f"/api/v1/printers/{printer.id}/axis-jog?axis=x&distance=181&limit=181")
        assert response.status_code == 400
        assert "<= 180 mm" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_axis_jog_allows_h2s_travel_above_legacy_cap(self, async_client: AsyncClient, printer_factory):
        printer = await printer_factory(name="H2S-Test", model="H2S")
        mock_client = MagicMock()
        mock_client.send_gcode.return_value = True
        with patch("backend.app.api.routes.printers.printer_manager") as mock_pm:
            mock_pm.get_client.return_value = mock_client
            response = await async_client.post(
                f"/api/v1/printers/{printer.id}/axis-jog?axis=x&distance=300&limit=300"
            )
            assert response.status_code == 200
            assert "G1 X300.00 F3000" in mock_client.send_gcode.call_args[0][0]

    @pytest.mark.asyncio
    async def test_axis_jog_rejects_speed_outside_axis_range(self, async_client: AsyncClient, printer_factory):
        printer = await printer_factory(name="P1")
        response = await async_client.post(f"/api/v1/printers/{printer.id}/axis-jog?axis=z&distance=5&speed=5000")
        assert response.status_code == 400
        assert "speed" in response.json()["detail"].lower()


class TestTemperatureControlAPI:
    @pytest.mark.asyncio
    async def test_set_temperature_not_found(self, async_client: AsyncClient):
        response = await async_client.post("/api/v1/printers/99999/temperature?target=nozzle&temperature=200")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_set_nozzle_temperature_success(self, async_client: AsyncClient, printer_factory):
        printer = await printer_factory(name="P1")
        mock_client = MagicMock()
        mock_client.set_nozzle_temperature.return_value = True
        with patch("backend.app.api.routes.printers.printer_manager") as mock_pm:
            mock_pm.get_client.return_value = mock_client
            response = await async_client.post(
                f"/api/v1/printers/{printer.id}/temperature?target=nozzle&temperature=215&nozzle=1"
            )
            assert response.status_code == 200
            mock_client.set_nozzle_temperature.assert_called_once_with(215, 1)

    @pytest.mark.asyncio
    async def test_set_bed_temperature_success(self, async_client: AsyncClient, printer_factory):
        printer = await printer_factory(name="P1")
        mock_client = MagicMock()
        mock_client.set_bed_temperature.return_value = True
        with patch("backend.app.api.routes.printers.printer_manager") as mock_pm:
            mock_pm.get_client.return_value = mock_client
            response = await async_client.post(
                f"/api/v1/printers/{printer.id}/temperature?target=bed&temperature=60"
            )
            assert response.status_code == 200
            mock_client.set_bed_temperature.assert_called_once_with(60)

    @pytest.mark.asyncio
    async def test_set_temperature_rejects_out_of_range(self, async_client: AsyncClient, printer_factory):
        printer = await printer_factory(name="P1")
        response = await async_client.post(
            f"/api/v1/printers/{printer.id}/temperature?target=bed&temperature=200"
        )
        assert response.status_code == 400
        assert "temperature" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_set_chamber_temperature_rejects_unsupported_model(self, async_client: AsyncClient, printer_factory):
        printer = await printer_factory(name="A1-Mini-Test", model="A1 Mini")
        response = await async_client.post(
            f"/api/v1/printers/{printer.id}/temperature?target=chamber&temperature=45"
        )
        assert response.status_code == 400
        assert "chamber" in response.json()["detail"].lower()


class TestExtrudeAPI:
    @pytest.mark.asyncio
    async def test_extrude_not_found(self, async_client: AsyncClient):
        response = await async_client.post("/api/v1/printers/99999/extrude?amount=5")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_extrude_rejects_cold_nozzle(self, async_client: AsyncClient, printer_factory):
        printer = await printer_factory(name="P1")
        mock_client = MagicMock()
        mock_state = MagicMock()
        mock_state.temperatures = {"nozzle": 120}
        with patch("backend.app.api.routes.printers.printer_manager") as mock_pm:
            mock_pm.get_client.return_value = mock_client
            mock_pm.get_status.return_value = mock_state
            response = await async_client.post(f"/api/v1/printers/{printer.id}/extrude?amount=5&speed=300")
            assert response.status_code == 400
            assert "nozzle" in response.json()["detail"].lower()
            mock_client.send_gcode.assert_not_called()

    @pytest.mark.asyncio
    async def test_extrude_sends_relative_extrusion_gcode(self, async_client: AsyncClient, printer_factory):
        printer = await printer_factory(name="P1")
        mock_client = MagicMock()
        mock_client.send_gcode.return_value = True
        mock_state = MagicMock()
        mock_state.temperatures = {"nozzle": 205}
        with patch("backend.app.api.routes.printers.printer_manager") as mock_pm:
            mock_pm.get_client.return_value = mock_client
            mock_pm.get_status.return_value = mock_state
            response = await async_client.post(f"/api/v1/printers/{printer.id}/extrude?amount=-4&speed=240")
            assert response.status_code == 200
            mock_client.send_gcode.assert_called_once_with("M83\nG1 E-4.00 F240\nM82")


class TestHomeAxesAPI:
    @pytest.mark.asyncio
    async def test_home_axes_not_found(self, async_client: AsyncClient):
        response = await async_client.post("/api/v1/printers/99999/home-axes?axes=z")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_home_axes_invalid(self, async_client: AsyncClient, printer_factory):
        printer = await printer_factory(name="P1")
        response = await async_client.post(f"/api/v1/printers/{printer.id}/home-axes?axes=bogus")
        assert response.status_code == 400

    @pytest.mark.asyncio
    @pytest.mark.parametrize("axes", ["z", "xy", "all"])
    async def test_home_axes_always_runs_full_home(self, async_client: AsyncClient, printer_factory, axes):
        # Regression for #1052: regardless of the axes argument, the endpoint must send a bare
        # `G28` so the printer's safe auto-home sequence (toolhead park → XY home → Z home) runs.
        # Sending `G28 Z` alone on H2C/H2D/H2S/X1 can crash the bed into the toolhead.
        printer = await printer_factory(name="P1")
        mock_client = MagicMock()
        mock_client.send_gcode.return_value = True
        with patch("backend.app.api.routes.printers.printer_manager") as mock_pm:
            mock_pm.get_client.return_value = mock_client
            response = await async_client.post(f"/api/v1/printers/{printer.id}/home-axes?axes={axes}")
            assert response.status_code == 200
            mock_client.send_gcode.assert_called_once_with("G28")

    @pytest.mark.asyncio
    async def test_home_axes_not_connected(self, async_client: AsyncClient, printer_factory):
        printer = await printer_factory(name="D")
        with patch("backend.app.api.routes.printers.printer_manager") as mock_pm:
            mock_pm.get_client.return_value = None
            response = await async_client.post(f"/api/v1/printers/{printer.id}/home-axes?axes=z")
            assert response.status_code == 400

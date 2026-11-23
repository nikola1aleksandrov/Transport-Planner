
import unittest

from main import (
    BalancedStrategy,
    BicycleTransport,
    BusTransport,
    CarTransport,
    CheapestStrategy,
    FastestStrategy,
    Route,
    TransportFactory,
    TransportPlannerFacade,
    WalkingTransport,
)


class TransportTests(unittest.TestCase):

    def setUp(self):
        self.route = Route(12, True, True, True, 1.55)

    def test_positive_distance_required(self):
        with self.assertRaises(ValueError):
            Route(0, True, True, True)

    def test_negative_fuel_price_rejected(self):
        with self.assertRaises(ValueError):
            Route(10, True, True, True, -1)

    def test_factory_creates_requested_type(self):
        self.assertIsInstance(
            TransportFactory.create("bike"), BicycleTransport
        )

    def test_factory_rejects_unknown_type(self):
        with self.assertRaises(ValueError):
            TransportFactory.create("helicopter")

    def test_walking_has_zero_cost(self):
        result = WalkingTransport().evaluate(self.route)
        self.assertTrue(result.possible)
        self.assertEqual(result.duration_min, 144.0)
        self.assertEqual(result.total_cost_eur, 0.0)

    def test_walking_not_possible_above_limit(self):
        route = Route(31, True, True, True)
        self.assertFalse(WalkingTransport().evaluate(route).possible)

    def test_bicycle_requires_bike_lanes(self):
        route = Route(5, True, False, True)
        self.assertFalse(BicycleTransport().evaluate(route).possible)

    def test_car_requires_road_access(self):
        route = Route(5, True, True, False)
        self.assertFalse(CarTransport().evaluate(route).possible)

    def test_car_cost_is_distance_times_consumption(self):
        result = CarTransport().evaluate(self.route)
        self.assertEqual(result.fuel_cost_eur, 1.21)
        self.assertEqual(result.total_cost_eur, result.fuel_cost_eur)

    def test_bus_requires_public_transport(self):
        route = Route(5, False, True, True)
        self.assertFalse(BusTransport().evaluate(route).possible)

    def test_bus_fuel_and_ticket_separate(self):
        result = BusTransport().evaluate(self.route)
        self.assertEqual(result.fuel_cost_eur, 0.0)
        self.assertEqual(result.total_cost_eur, 1.50)

    def test_fastest_strategy_chooses_car_for_demo(self):
        _, recommendation = TransportPlannerFacade().analyze(
            self.route,
            ["walk", "bike", "car", "bus"],
            FastestStrategy()
        )
        self.assertEqual(recommendation.code, "car")

    def test_cheapest_strategy_chooses_bike(self):
        _, recommendation = TransportPlannerFacade().analyze(
            self.route,
            ["walk", "bike", "car", "bus"],
            CheapestStrategy()
        )
        self.assertEqual(recommendation.code, "bike")

    def test_balanced_strategy_selects_one_feasible(self):
        results, recommendation = TransportPlannerFacade().analyze(
            self.route,
            ["walk", "bike", "car", "bus"],
            BalancedStrategy()
        )
        self.assertIn(recommendation, results)
        self.assertTrue(recommendation.possible)

    def test_unavailable_modes_give_no_recommendation(self):
        route = Route(15, False, False, False)
        reports, recommendation = TransportPlannerFacade().analyze(
            route,
            ["bike", "car", "bus"],
            FastestStrategy()
        )
        self.assertIsNone(recommendation)
        self.assertTrue(
            all(not result.possible for result in reports)
        )

    def test_empty_preferences_are_rejected(self):
        with self.assertRaises(ValueError):
            TransportPlannerFacade().analyze(
                self.route, [], BalancedStrategy()
            )

    def test_duplicate_preference_removed(self):
        reports, _ = TransportPlannerFacade().analyze(
            self.route,
            ["walk", "walk", "car"],
            FastestStrategy()
        )
        self.assertEqual(
            [item.code for item in reports],
            ["walk", "car"]
        )

    def test_hilly_terrain_increases_bicycle_time(self):
        flat = BicycleTransport().evaluate(self.route)
        hilly = BicycleTransport().evaluate(
            Route(12, True, True, True, 1.55, True)
        )
        self.assertGreater(hilly.duration_min, flat.duration_min)


if __name__ == "__main__":
    unittest.main()

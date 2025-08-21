"""Tests for the BaseAnalyzer class."""

import unittest

from arazzo_generator.analyzers.base_analyzer import BaseAnalyzer


class TestBaseAnalyzer(unittest.TestCase):
    """Tests for the BaseAnalyzer class."""

    def test_init(self):
        """Test initialization of the BaseAnalyzer."""

        # Create a concrete subclass for testing since BaseAnalyzer is abstract
        class ConcreteAnalyzer(BaseAnalyzer):
            def analyze(self):
                return []

        # Test with endpoints only
        endpoints = {"path1": {"get": {}}, "path2": {"post": {}}}
        analyzer = ConcreteAnalyzer(endpoints)
        self.assertEqual(analyzer.endpoints, endpoints)
        self.assertEqual(analyzer.relationships, {})
        self.assertEqual(analyzer.workflows, [])

        # Test with endpoints and relationships
        relationships = {"path1": ["path2"]}
        analyzer = ConcreteAnalyzer(endpoints, relationships)
        self.assertEqual(analyzer.endpoints, endpoints)
        self.assertEqual(analyzer.relationships, relationships)
        self.assertEqual(analyzer.workflows, [])

    def test_get_workflows(self):
        """Test get_workflows method."""

        # Create a concrete subclass for testing
        class ConcreteAnalyzer(BaseAnalyzer):
            def analyze(self):
                self.workflows = [{"name": "workflow1"}, {"name": "workflow2"}]
                return self.workflows

        # Initialize analyzer and set workflows
        analyzer = ConcreteAnalyzer({})
        analyzer.workflows = [{"name": "workflow1"}, {"name": "workflow2"}]

        # Test get_workflows
        workflows = analyzer.get_workflows()
        self.assertEqual(len(workflows), 2)
        self.assertEqual(workflows[0]["name"], "workflow1")
        self.assertEqual(workflows[1]["name"], "workflow2")

    def test_analyze_abstract(self):
        """Test that BaseAnalyzer.analyze is abstract and must be implemented by subclasses."""
        # Attempting to instantiate BaseAnalyzer directly should raise TypeError
        with self.assertRaises(TypeError):
            BaseAnalyzer({})


if __name__ == "__main__":
    unittest.main()

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>
#include "engine.h"

namespace py = pybind11;
using namespace logdog;

PYBIND11_MODULE(_logdog_core, m) {
    m.doc() = "LogDog C++ Core Module";

    py::enum_<EventType>(m, "EventType")
        .value("StateActivated", EventType::StateActivated)
        .value("StateCompleted", EventType::StateCompleted)
        .value("Timeout", EventType::Timeout)
        .value("StateInterrupted", EventType::StateInterrupted)
        .value("EntryDetected", EventType::EntryDetected)
        .value("EngineLog", EventType::EngineLog)
        .export_values();

    py::class_<EventData>(m, "EventData")
        .def_readonly("type", &EventData::type)
        .def_readonly("state_name", &EventData::state_name)
        .def_readonly("node_name", &EventData::node_name)
        .def_readonly("description", &EventData::description)
        .def_readonly("elapsed_ms", &EventData::elapsed_ms);

    py::class_<Engine>(m, "Engine")
        .def(py::init<const std::string&, double>())
        .def("add_state_rule", &Engine::add_state_rule)
        .def("set_completion_nodes", &Engine::set_completion_nodes)
        .def("add_entry_node", &Engine::add_entry_node)
        .def("set_callback", &Engine::set_callback)
        .def("run", &Engine::run, py::call_guard<py::gil_scoped_release>())
        .def("stop", &Engine::stop);
}
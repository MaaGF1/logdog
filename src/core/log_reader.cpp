#include "log_reader.h"
#include <iostream>
#include <thread>
#include <chrono>

namespace logdog {

LogReader::LogReader(const std::string& path) : path_(path), last_pos_(0) {}

bool LogReader::open() {
    file_.open(path_, std::ios::in);
    if (!file_.is_open()) return false;
    
    // Seek to end initially
    file_.seekg(0, std::ios::end);
    // file_.seekg(0, std::ios::beg); 
    last_pos_ = file_.tellg();
    return true;
}

void LogReader::close() {
    if (file_.is_open()) file_.close();
}

std::vector<std::string> LogReader::read_new_lines() {
    std::vector<std::string> lines;

    if (!file_.is_open()) return lines;
    file_.clear();
    file_.sync();

    std::string line;
    while (std::getline(file_, line)) {
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        if (!line.empty()) {
            lines.push_back(line);
        }
    }
    last_pos_ = file_.tellg();

    return lines;
}

}
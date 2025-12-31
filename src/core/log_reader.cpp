#include "log_reader.h"
#include <iostream>
#include <filesystem>
#include <thread>

namespace logdog {

namespace fs = std::filesystem;

LogReader::LogReader(const std::string& path) 
    : path_(path), last_pos_(0), initialized_(false) {}

bool LogReader::open() {
    // 只是单纯的打开文件，不做 Seek 操作
    file_.open(path_, std::ios::in);
    return file_.is_open();
}

void LogReader::close() {
    if (file_.is_open()) {
        file_.close();
    }
}

std::vector<std::string> LogReader::read_new_lines() {
    std::vector<std::string> lines;
    std::error_code ec;

    // 1. File exist
    if (!fs::exists(path_, ec)) {
        close();
        return lines;
    }

    // 2. Calculate Size
    uintmax_t current_size = fs::file_size(path_, ec);
    if (ec) {
        return lines; 
    }

    // 3. Initial startup logic: Jump to the end of the file
    if (!initialized_) {
        last_pos_ = current_size;
        initialized_ = true;
        return lines; 
    }

    // 4. Rotation check: Update postion
    if (current_size < static_cast<uintmax_t>(last_pos_)) {
        std::cout << "[LogDog] Log rotation detected (Truncated). Resetting position." << std::endl;
        
        close(); 
        last_pos_ = 0;
    }

    // 5. File open
    if (!file_.is_open()) {
        if (!open()) return lines;
    }

    // 6. Ready
    file_.clear();
    file_.seekg(last_pos_);

    std::string line;
    while (std::getline(file_, line)) {
        // Windows \r
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        if (!line.empty()) {
            lines.push_back(line);
        }
    }

    // 7. Update read pos
    if (file_.eof()) {
        file_.clear();
    }
    last_pos_ = file_.tellg();

    if (last_pos_ == std::streampos(-1)) {
        last_pos_ = current_size;
    }

    return lines;
}

}
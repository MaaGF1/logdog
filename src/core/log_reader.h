#pragma once
#include <string>
#include <fstream>
#include <vector>

namespace logdog {

class LogReader {
public:
    LogReader(const std::string& path);
    bool open();
    std::vector<std::string> read_new_lines();
    void close();

private:
    std::string path_;
    std::ifstream file_;
    std::streampos last_pos_;
};

}
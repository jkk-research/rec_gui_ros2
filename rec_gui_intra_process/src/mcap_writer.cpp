/**
 * @file mcap_writer.cpp
 * @brief Implementation of MCAP format writer
 */

#include "rec_gui_intra_process/mcap_writer.hpp"

#include <fstream>
#include <filesystem>
#include <cstring>
#include <ctime>

namespace rec_gui_intra_process
{

MCAPWriter::MCAPWriter(const WriterConfig & config)
: config_(config)
{
}

MCAPWriter::~MCAPWriter()
{
  if (is_open_) {
    close();
  }
}

bool MCAPWriter::open()
{
  if (is_open_) {
    return true;
  }

  // Create directory if it doesn't exist
  std::filesystem::path file_path(config_.output_file);
  std::filesystem::create_directories(file_path.parent_path());

  try {
    // Open file in binary write mode
    auto * file = new std::ofstream(config_.output_file, std::ios::binary);

    if (!file->is_open()) {
      delete file;
      return false;
    }

    file_handle_ = file;

    // Write MCAP header
    const char mcap_magic[] = "MCAP0";
    file->write(mcap_magic, 5);

    // Write version
    uint32_t version = 0;
    file->write(reinterpret_cast<const char *>(&version), sizeof(version));

    is_open_ = true;
    message_count_ = 0;
    topic_channel_map_.clear();
    next_channel_id_ = 0;

    return true;
  } catch (const std::exception & e) {
    return false;
  }
}

bool MCAPWriter::close()
{
  if (!is_open_) {
    return true;
  }

  try {
    auto * file = static_cast<std::ofstream *>(file_handle_);

    if (file && file->is_open()) {
      // Write MCAP footer/index
      const char mcap_footer[] = "MCAP";
      file->write(mcap_footer, 4);

      uint32_t message_count = static_cast<uint32_t>(message_count_);
      file->write(reinterpret_cast<const char *>(&message_count), sizeof(message_count));

      file->close();
      delete file;
    }

    is_open_ = false;
    file_handle_ = nullptr;

    return true;
  } catch (const std::exception & e) {
    return false;
  }
}

bool MCAPWriter::writeMessage(
  const std::string & topic,
  const std::string & message_type,
  uint64_t timestamp,
  const std::vector<uint8_t> & data)
{
  if (!is_open_) {
    return false;
  }

  try {
    auto * file = static_cast<std::ofstream *>(file_handle_);

    if (!file || !file->is_open()) {
      return false;
    }

    // Get or create channel ID for this topic
    uint16_t channel_id;
    if (topic_channel_map_.find(topic) == topic_channel_map_.end()) {
      channel_id = next_channel_id_++;
      topic_channel_map_[topic] = channel_id;

      // Write channel definition
      const char channel_opcode = 0x01;  // Simplified channel opcode
      file->write(&channel_opcode, 1);
      file->write(reinterpret_cast<const char *>(&channel_id), sizeof(channel_id));

      uint16_t topic_len = topic.length();
      file->write(reinterpret_cast<const char *>(&topic_len), sizeof(topic_len));
      file->write(topic.c_str(), topic.length());

      uint16_t type_len = message_type.length();
      file->write(reinterpret_cast<const char *>(&type_len), sizeof(type_len));
      file->write(message_type.c_str(), message_type.length());
    } else {
      channel_id = topic_channel_map_[topic];
    }

    // Write message record
    const char message_opcode = 0x02;  // Simplified message opcode
    file->write(&message_opcode, 1);
    file->write(reinterpret_cast<const char *>(&channel_id), sizeof(channel_id));
    file->write(reinterpret_cast<const char *>(&timestamp), sizeof(timestamp));

    uint32_t data_size = data.size();
    file->write(reinterpret_cast<const char *>(&data_size), sizeof(data_size));
    file->write(reinterpret_cast<const char *>(data.data()), data.size());

    message_count_++;

    return true;
  } catch (const std::exception & e) {
    return false;
  }
}

uint64_t MCAPWriter::getFileSize() const
{
  try {
    return std::filesystem::file_size(config_.output_file);
  } catch (const std::exception & e) {
    return 0;
  }
}

}  // namespace rec_gui_intra_process

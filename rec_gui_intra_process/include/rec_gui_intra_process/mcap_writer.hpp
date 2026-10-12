/**
 * @file mcap_writer.hpp
 * @brief MCAP format writer for recording ROS 2 messages
 */

#ifndef REC_GUI_INTRA_PROCESS__MCAP_WRITER_HPP_
#define REC_GUI_INTRA_PROCESS__MCAP_WRITER_HPP_

#include <memory>
#include <string>
#include <vector>
#include <map>

#include "rclcpp/rclcpp.hpp"

namespace rec_gui_intra_process
{

class MCAPWriter
{
public:
  enum class CompressionType
  {
    NONE = 0,
    ZSTD = 1,
  };

  struct WriterConfig
  {
    std::string output_file;
    CompressionType compression = CompressionType::ZSTD;
    uint32_t chunk_size = 52428800;  // 50 MB
    uint32_t compression_level = 6;
  };

  explicit MCAPWriter(const WriterConfig & config);
  ~MCAPWriter();

  /**
   * Open the MCAP file for writing
   * @return true if file opened successfully
   */
  bool open();

  /**
   * Close the MCAP file
   * @return true if file closed successfully
   */
  bool close();

  /**
   * Write a message to the MCAP file
   * @param topic Topic name
   * @param message_type Message type string
   * @param timestamp Timestamp in nanoseconds
   * @param data Serialized message data
   * @return true if message was written successfully
   */
  bool writeMessage(
    const std::string & topic,
    const std::string & message_type,
    uint64_t timestamp,
    const std::vector<uint8_t> & data);

  /**
   * Check if the writer is open
   * @return true if file is open
   */
  bool isOpen() const { return is_open_; }

  /**
   * Get the number of messages written
   * @return Number of messages written
   */
  uint64_t getMessageCount() const { return message_count_; }

  /**
   * Get the file size in bytes
   * @return File size in bytes
   */
  uint64_t getFileSize() const;

private:
  WriterConfig config_;
  bool is_open_{false};
  uint64_t message_count_{0};
  std::map<std::string, uint16_t> topic_channel_map_;
  uint16_t next_channel_id_{0};

  // Placeholder for actual MCAP file handle
  void * file_handle_{nullptr};
};

}  // namespace rec_gui_intra_process

#endif  // REC_GUI_INTRA_PROCESS__MCAP_WRITER_HPP_

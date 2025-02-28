terraform {
  required_providers {
    huaweicloud = {
      source = "huaweicloud/huaweicloud"
    }
  }
}

# Create new configuration first
resource "huaweicloud_as_configuration" "asg_config_new" {
  scaling_configuration_name = "asg_config_${var.template_version}"
  instance_config {
    image    = var.image_id
    flavor   = var.flavor_id
    key_name = var.key_name
    security_group_ids = [var.security_group_id]
    disk {
      size        = 40
      volume_type = "SAS"
      disk_type   = "SYS"
    }
  }
}

# Update ASG to use new configuration
resource "huaweicloud_as_group" "asg_group" {
  scaling_group_name = "asg_group"
  scaling_configuration_id = huaweicloud_as_configuration.asg_config_new.id
  desire_instance_number = var.desired_capacity
  min_instance_number    = var.min_size
  max_instance_number    = var.max_size
  vpc_id = var.vpc_id
  networks {
    id = var.subnet_id
  }
  
  # Add this to ensure zero-downtime
  instance_terminate_policy = "OLD_CONFIG_OLD_INSTANCE"
  cool_down_time = 300

    lifecycle {
    create_before_destroy = true
  }

}



# Variables
variable "template_version" {}
variable "image_id" {}
variable "flavor_id" {}
variable "key_name" {}
variable "desired_capacity" {}
variable "min_size" {}
variable "max_size" {}
variable "security_group_id" {}
variable "vpc_id" {}
variable "subnet_id" {}
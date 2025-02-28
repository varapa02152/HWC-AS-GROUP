import subprocess
import time
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkas.v1.region.as_region import AsRegion
from huaweicloudsdkas.v1 import *

class ASGUpdater:
    def __init__(self):
        self.credentials = BasicCredentials(
            ak="BYJ15CSXRF44ONZK1HAG",          
            sk="u4DdWpG7pU59DCjOHCsOvzOI9HQcq22OqnV1HbUG"           
        )
        self.client = AsClient.new_builder() \
            .with_credentials(self.credentials) \
            .with_region(AsRegion.value_of("ap-southeast-2")) \
            .build()

    def get_asg_id(self, group_name):
        try:
            request = ListScalingGroupsRequest()
            response = self.client.list_scaling_groups(request)
            for group in response.scaling_groups:
                if group.scaling_group_name == group_name:
                    return group.scaling_group_id
            print(f"No ASG found with name: {group_name}")
            return None
        except Exception as e:
            print(f"Error getting ASG ID: {e}")
            return None

    def get_instance_list(self, group_id):
        try:
            request = ListScalingInstancesRequest()
            request.scaling_group_id = group_id
            response = self.client.list_scaling_instances(request)
            return response.scaling_group_instances
        except Exception as e:
            print(f"Error getting instance list: {e}")
            return []

    def force_instance_refresh(self, group_id):
        try:
            print("\n=== Starting Instance Refresh ===")
            
            # Get current instances
            print("\nChecking current instances...")
            current_instances = self.get_instance_list(group_id)
            if current_instances:
                print(f"Found {len(current_instances)} current instances:")
                for instance in current_instances:
                    print(f"- Instance ID: {instance.instance_id}")
            else:
                print("No current instances found")

            # First, set min instances to 0 temporarily
            print("\nModifying group capacity...")
            modify_request = UpdateScalingGroupRequest()
            modify_request.scaling_group_id = group_id
            modify_request.body = UpdateScalingGroupOption(
                min_instance_number=0,
                desire_instance_number=0
            )
            self.client.update_scaling_group(modify_request)
            print("Group capacity modified")

            # Remove existing instances
            if current_instances:
                print("\nRemoving existing instances...")
                remove_request = BatchRemoveScalingInstancesRequest()
                remove_request.scaling_group_id = group_id
                remove_request.body = BatchRemoveInstancesOption(
                    instances_id=[inst.instance_id for inst in current_instances],  # Changed from 'instances' to 'instances_id'
                    action="REMOVE",
                    instance_delete="yes"
                )
                self.client.batch_remove_scaling_instances(remove_request)
                print("Removal request sent successfully")
                
                print("Waiting for instances to be removed...")
                time.sleep(120)

            # Reset group capacity to original values
            print("\nResetting group capacity...")
            reset_request = UpdateScalingGroupRequest()
            reset_request.scaling_group_id = group_id
            reset_request.body = UpdateScalingGroupOption(
                min_instance_number=1,
                desire_instance_number=2,
                delete_publicip=True,  # Added this to ensure complete cleanup
                delete_volume=True     # Added this to ensure complete cleanup
            )
            self.client.update_scaling_group(reset_request)
            print("Group capacity reset")
            
            # Wait for new instances
            print("Waiting for new instances to be created...")
            time.sleep(180)
            
            # Check new instances
            new_instances = self.get_instance_list(group_id)
            if new_instances:
                print(f"\nNew instances created ({len(new_instances)}):")
                for instance in new_instances:
                    print(f"- Instance ID: {instance.instance_id}")
            else:
                print("\nNo new instances found yet")
            
            print("\n=== Instance Refresh Completed ===")
            
        except Exception as e:
            print(f"\nError during instance refresh: {e}")
            raise  # Added to see full error trace

    def apply_new_configuration(self, new_image_id, template_version, group_name):
        try:
            print("\n=== Starting Configuration Update ===")
            
            print(f"\nUpdating configuration with:")
            print(f"- New Image ID: {new_image_id}")
            print(f"- Template Version: {template_version}")
            
            # Create terraform vars file
            print("\nCreating terraform.tfvars file...")
            with open("terraform.tfvars", "w") as f:
                f.write(f'''
                    template_version = "{template_version}"
                    image_id = "{new_image_id}"
                    flavor_id = "s6.small.1"
                    key_name = "KeyPair-fah"
                    desired_capacity = 2
                    min_size = 1
                    max_size = 3
                    security_group_id = "3eb94c45-4f06-43b4-9b02-ba9edbfb8851"
                    vpc_id = "41d7ce64-0158-4ad5-b487-5aca02fbd0a7"
                    subnet_id = "15f824ec-514b-4c86-895c-9db12180482c"
                ''')

            print("\nInitializing Terraform...")
            subprocess.run(["terraform", "init"], check=True)
            
            print("\nApplying new configuration...")
            subprocess.run(["terraform", "apply", "-auto-approve"], check=True)
            
            print("\nGetting ASG ID for group name:", group_name)
            group_id = self.get_asg_id(group_name)
            if not group_id:
                print(f"Error: ASG with name '{group_name}' not found.")
                return
            
            print("\nStarting instance refresh process...")
            self.force_instance_refresh(group_id)
            
            # print("\nWaiting for cool down period...")
            time.sleep(100)
            
            print("\n=== Update Process Completed Successfully! ===")
            
        except subprocess.CalledProcessError as e:
            print(f"\nError during terraform execution: {e}")
        except Exception as e:
            print(f"\nError during update: {e}")
            raise  # Added to see full error trace

# Usage
if __name__ == "__main__":
    print("\n=== Auto Scaling Group Update Tool ===")
    updater = ASGUpdater()
    updater.apply_new_configuration(
        new_image_id="9021460a-daaf-4078-b4b8-91db32440f24",
        template_version="v5",
        group_name="asg_group"  # Replace with your ASG name
    )
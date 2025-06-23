using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using System;
//using Unity.Robotics.ROSTCPConnector.
using RosMessageTypes.Std;
//using RosMessageTypes.Sensor;
using Unity.VisualScripting;


public class RosTimeController : MonoBehaviour
{
    
    public bool paused = true;
    public bool stepModeEnabled = true;
    /*public float currentRewardSum = 0;

    public static void ApplyReward(float r)
    {
        instance.currentRewardSum += r;
    }*/

    /*public bool episodeDone = false;
    public static void EndEpisode()
    {
        instance.episodeDone = true;
    }*/

    public delegate void OnGlobalSensorsRequest();
    public static OnGlobalSensorsRequest onGlobalSensorsRequest;


    public static bool IsPaused()
    {
        if (instance == null || instance.paused)
        {
            return true;
        }
        return false;
    }
    

    static RosTimeController instance;
    public static bool AsyncSensingAllowed()
    {
        if (instance == null || instance.stepModeEnabled)
        {
            return false;
        }
        return true;
    }

    public String step_topic_name = "/step";
    public String step_end_topic_name = "/step_finished";
    public String serviceName = "/step_srv";
    //public String episodeStateTopicName = "/episode_done";
    //public String rewardTopicName = "/reward";
    

    public float maxTimeScale = 200;

    public int numSteps = 0;
    public int numFixedUpdates = 0;
    public int numFixedUpdatesLastStep = 0;

    public int numFixedUpdatesPerGymStep = 5;
    ROSConnection conn;

    // Start is called before the first frame update
    void Start()
    {
        /* m_ROS = ROSConnection.GetOrCreateInstance(); */
        //ROSConnection.GetOrCreateInstance().Unsubscribe(topic_name);
        //
        /* ROSConnection.GetOrCreateInstance().Subscribe<EmptyMsg>(step_topic_name, StepTime); */
        /* ROSConnection.GetOrCreateInstance().RegisterPublisher<EmptyMsg>(step_end_topic_name); */
        /* ROSConnection.GetOrCreateInstance().Subscribe<Int8Msg>(step_topic_name, StepTime); */
        /* ROSConnection.GetOrCreateInstance().RegisterPublisher<Int8Msg>(step_end_topic_name); */
        instance = this;
        conn = ROSConnection.GetOrCreateInstance();
        conn.ImplementService<TriggerRequest, TriggerResponse>(serviceName, StepSrvResp);

        /* Physics.simulationMode = SimulationMode.Script; */
    }

    TriggerResponse StepSrvResp(TriggerRequest req){
      /* Debug.Log("KOCKA"); */

      return new TriggerResponse();
    }

    // Update is called once per frame
    void Update()
    {

        /* if (Time.deltaTime > 0) */
        /* { */
        /*     Debug.Log("Nonzero DT Update"); */
        /* } */
        //Debug.Log("Normal Update, DT: " + Time.deltaTime);
    }

    public void StepTime(Int8Msg msg)
    {
        return;

        if(!paused){
          return;
        }
        Debug.Log("-------STEP! ID: " + ((int)msg.data));
        //Time.fixedDeltaTime = 0.2f;
        //Time.timeScale = maxTimeScale;
        
        Time.timeScale = 0;
        //Time.fixedDeltaTime = 0.02f * Time.timeScale;
        paused = false;
        Debug.Log("----- num fixed updates since last step: " + (numFixedUpdates - numFixedUpdatesLastStep));

        /* Physics.Simulate(Time.fixedDeltaTime); */

        Debug.Log("PERFORMING SENSING FOR GYM STEP! Time: " + Time.time);
        /* onGlobalSensorsRequest?.Invoke(); */
        numFixedUpdates += 1;
        

            // SIGNIFY STEP END!
        /* ROSConnection.GetOrCreateInstance().Publish(step_end_topic_name, new Int8Msg((sbyte)numFixedUpdates)); */
        conn.Publish(step_end_topic_name, new Int8Msg((sbyte)numFixedUpdates));
        paused = true;

        //numFixedUpdatesLastStep = numFixedUpdates;
    }

    void FixedUpdate()
    {
        return;
        
        Time.timeScale = 0;
        paused = true;
        numFixedUpdates += 1;
        //Debug.Log("Fixed index: " + numFixedUpdates);
        Debug.Log("FIXED! Game time is: " + Time.time + " Index: " + numFixedUpdates);

        if (numFixedUpdates - numFixedUpdatesLastStep == numFixedUpdatesPerGymStep)
        {
            
            // INVOKE SENSORS
            Debug.Log("PERFORMING SENSING FOR GYM STEP! Time: " + Time.time);
            onGlobalSensorsRequest?.Invoke();
            numFixedUpdatesLastStep = numFixedUpdates;

            // SIGNIFY STEP END!
            ROSConnection.GetOrCreateInstance().Publish(step_end_topic_name, new Int8Msg((sbyte)numFixedUpdates));
        }

    }
}
